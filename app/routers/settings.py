"""Paramètres & matrice d'accès — super administrateur uniquement."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
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
    ROLE_ADMINISTRATION_VENTES,
    ROLE_ADMINISTRATION_TECHNIQUE,
    ROLE_DIRECTION,
    ROLE_LOGISTIQUE,
    ROLE_COMPTABILITE,
    ROLE_EXPEDITION,
    ROLE_COMMERCIAL,
    ROLES_ADMIN,
    SUPERADMIN_EMAIL,
    default_app_access_for_role,
    APPS_CATALOG,
    ACCESS_LEVELS,
    LEVEL_LABELS,
    LEVEL_ORDER,
    is_known_app_module,
)
from app.services.audit_service import log_action
from services.auth_service import get_current_user, require_settings, merged_app_access, parse_access_overrides_raw

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


# ─── Labels rôles (partagés par les endpoints d'accès) ────────────

_ROLE_LABELS = {
    ROLE_DIRECTION: "Direction",
    ROLE_ADMINISTRATION: "Administration",
    ROLE_ADMINISTRATION_VENTES: "Administration des ventes",
    ROLE_ADMINISTRATION_TECHNIQUE: "Administration technique",
    ROLE_FABRICATION: "Fabrication",
    ROLE_LOGISTIQUE: "Logistique",
    ROLE_COMPTABILITE: "Comptabilité",
    ROLE_EXPEDITION: "Expédition",
    ROLE_COMMERCIAL: "Commercial",
    ROLE_SUPERADMIN: "Super admin",
}


def _load_all_access(conn):
    """Charge role_access_defaults + user_access_overrides en 2 requêtes.

    Retourne (role_defaults, user_overrides) où :
    - role_defaults[role][(app, module)] = level
    - user_overrides[user_id][(app, module)] = level
    """
    role_defaults: dict = {}
    for r in conn.execute(
        "SELECT role, app_id, module_id, level FROM role_access_defaults"
    ).fetchall():
        role_defaults.setdefault(r["role"], {})[(r["app_id"], r["module_id"])] = r["level"]
    user_overrides: dict = {}
    for r in conn.execute(
        "SELECT user_id, app_id, module_id, level FROM user_access_overrides"
    ).fetchall():
        user_overrides.setdefault(r["user_id"], {})[(r["app_id"], r["module_id"])] = r["level"]
    return role_defaults, user_overrides


def _effective_level(role, uid, app_id, module_id, role_defaults, user_overrides):
    """Résout le niveau effectif — user override → role default → 'none'."""
    if role == ROLE_SUPERADMIN:
        return "admin"
    if app_id == "settings":
        return "none"
    ov = user_overrides.get(uid, {})
    if (app_id, module_id) in ov:
        return ov[(app_id, module_id)]
    if module_id != "_app" and (app_id, "_app") in ov:
        return ov[(app_id, "_app")]
    d = role_defaults.get(role, {})
    if (app_id, module_id) in d:
        return d[(app_id, module_id)]
    if module_id != "_app" and (app_id, "_app") in d:
        return d[(app_id, "_app")]
    return "none"


@router.get("/api/settings/access-matrix")
def access_matrix(request: Request):
    """Matrice complète pour l'écran /settings → Matrice d'accès.

    Renvoie :
      - `apps` : catalogue APPS_CATALOG (apps + sous-modules + labels).
      - `levels` : liste ordonnée des niveaux disponibles.
      - `level_labels` : libellés lisibles des niveaux.
      - `roles`, `role_labels` : rôles assignables + libellés.
      - `users[]` : chaque utilisateur avec { id, email, nom, role, role_label,
        actif, last_login, access:{app_id:{module_id:level}}, overrides:[{app_id,
        module_id, level}] }.
    Le super admin apparaît en lecture seule côté UI.
    """
    require_settings(request)
    from database import get_db

    with get_db() as conn:
        users = conn.execute(
            "SELECT id, email, nom, role, actif, last_login FROM users "
            "ORDER BY actif DESC, role DESC, nom ASC"
        ).fetchall()
        role_defaults, user_overrides = _load_all_access(conn)

    users_out = []
    for u in users:
        d = dict(u)
        role = d["role"]
        acc = {}
        for app in APPS_CATALOG:
            aid = app["id"]
            acc[aid] = {"_app": _effective_level(role, d["id"], aid, "_app", role_defaults, user_overrides)}
            for m in app.get("modules", []):
                acc[aid][m["id"]] = _effective_level(role, d["id"], aid, m["id"], role_defaults, user_overrides)
        d["access"] = acc
        d["overrides"] = [
            {"app_id": a, "module_id": mid, "level": lvl}
            for (a, mid), lvl in sorted(user_overrides.get(d["id"], {}).items())
        ]
        d["role_label"] = _ROLE_LABELS.get(role, role)
        users_out.append(d)

    return {
        "apps": APPS_CATALOG,
        "levels": list(ACCESS_LEVELS),
        "level_labels": LEVEL_LABELS,
        "roles": sorted(ASSIGNABLE_ROLES | {ROLE_SUPERADMIN}),
        "role_labels": _ROLE_LABELS,
        "superadmin_email": SUPERADMIN_EMAIL,
        "users": users_out,
    }


class SetAccessBody(BaseModel):
    app_id: str
    module_id: str = "_app"
    level: Optional[str] = None  # None ou "" → suppression de la surcharge


@router.put("/api/settings/access-matrix/user/{user_id}")
def set_user_access(user_id: int, body: SetAccessBody, request: Request):
    """Écrit / supprime une surcharge d'accès pour un utilisateur.

    `level=None` (ou vide) supprime la ligne — l'utilisateur retombe sur le
    défaut de son rôle. Refuse d'éditer le rôle super admin (intouchable) et
    l'app `settings` (super admin uniquement, non surchargeable).
    """
    admin_user = require_settings(request)
    if body.app_id == "settings":
        raise HTTPException(status_code=400, detail="Paramètres non surchargeable (super admin uniquement).")
    if not is_known_app_module(body.app_id, body.module_id):
        raise HTTPException(status_code=400, detail=f"App/module inconnu : {body.app_id}/{body.module_id}")
    lvl = (body.level or "").strip().lower()
    if lvl and lvl not in ACCESS_LEVELS:
        raise HTTPException(status_code=400, detail=f"Niveau invalide : {body.level}")

    from database import get_db
    with get_db() as conn:
        u = conn.execute("SELECT id, role, nom, email FROM users WHERE id=?", (user_id,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
        if u["role"] == ROLE_SUPERADMIN:
            raise HTTPException(status_code=400, detail="Le super admin a tous les accès (non modifiable).")
        # Avant / après pour audit
        prev = conn.execute(
            "SELECT level FROM user_access_overrides WHERE user_id=? AND app_id=? AND module_id=?",
            (user_id, body.app_id, body.module_id),
        ).fetchone()
        prev_level = prev["level"] if prev else None
        if not lvl:
            conn.execute(
                "DELETE FROM user_access_overrides WHERE user_id=? AND app_id=? AND module_id=?",
                (user_id, body.app_id, body.module_id),
            )
        else:
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO user_access_overrides (user_id, app_id, module_id, level, updated_at, updated_by) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(user_id, app_id, module_id) DO UPDATE SET "
                "level=excluded.level, updated_at=excluded.updated_at, updated_by=excluded.updated_by",
                (user_id, body.app_id, body.module_id, lvl, now, admin_user.get("email", "")),
            )
        conn.commit()

    log_action(
        request,
        module="settings",
        action="UPDATE",
        objet=f"access:user:{u['email']}",
        detail=f"{body.app_id}/{body.module_id}: {prev_level or 'default'} → {lvl or 'default'}",
    )
    return {"ok": True, "app_id": body.app_id, "module_id": body.module_id, "level": lvl or None}


@router.get("/api/settings/role-defaults")
def role_defaults_endpoint(request: Request):
    """Référentiel rôles éditable — écran /settings → Référentiel rôles."""
    require_settings(request)
    from database import get_db
    with get_db() as conn:
        role_defaults, _ = _load_all_access(conn)

    out = []
    for role in sorted(ASSIGNABLE_ROLES | {ROLE_SUPERADMIN}):
        acc = {}
        for app in APPS_CATALOG:
            aid = app["id"]
            per_app = {"_app": _effective_level(role, 0, aid, "_app", role_defaults, {})}
            for m in app.get("modules", []):
                per_app[m["id"]] = _effective_level(role, 0, aid, m["id"], role_defaults, {})
            acc[aid] = per_app
        out.append({
            "role": role,
            "label": _ROLE_LABELS.get(role, role),
            "readonly": role == ROLE_SUPERADMIN,
            "access": acc,
            # Ce qui est explicitement défini en base (le reste hérite)
            "explicit": [
                {"app_id": a, "module_id": mid, "level": lvl}
                for (a, mid), lvl in sorted(role_defaults.get(role, {}).items())
            ],
        })

    return {
        "apps": APPS_CATALOG,
        "levels": list(ACCESS_LEVELS),
        "level_labels": LEVEL_LABELS,
        "roles": out,
    }


class SetRoleDefaultBody(BaseModel):
    app_id: str
    module_id: str = "_app"
    level: Optional[str] = None  # None → suppression (hérite du niveau parent)


@router.put("/api/settings/role-defaults/{role}")
def set_role_default(role: str, body: SetRoleDefaultBody, request: Request):
    """Édite le référentiel rôle. Refuse le super admin (intouchable) et l'app settings."""
    admin_user = require_settings(request)
    if role == ROLE_SUPERADMIN:
        raise HTTPException(status_code=400, detail="Le super admin a tous les accès (non modifiable).")
    if role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail=f"Rôle inconnu : {role}")
    if body.app_id == "settings":
        raise HTTPException(status_code=400, detail="Paramètres non modifiable (super admin uniquement).")
    if not is_known_app_module(body.app_id, body.module_id):
        raise HTTPException(status_code=400, detail=f"App/module inconnu : {body.app_id}/{body.module_id}")
    lvl = (body.level or "").strip().lower()
    if lvl and lvl not in ACCESS_LEVELS:
        raise HTTPException(status_code=400, detail=f"Niveau invalide : {body.level}")

    from database import get_db
    with get_db() as conn:
        prev = conn.execute(
            "SELECT level FROM role_access_defaults WHERE role=? AND app_id=? AND module_id=?",
            (role, body.app_id, body.module_id),
        ).fetchone()
        prev_level = prev["level"] if prev else None
        if not lvl:
            conn.execute(
                "DELETE FROM role_access_defaults WHERE role=? AND app_id=? AND module_id=?",
                (role, body.app_id, body.module_id),
            )
        else:
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO role_access_defaults (role, app_id, module_id, level, updated_at, updated_by) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(role, app_id, module_id) DO UPDATE SET "
                "level=excluded.level, updated_at=excluded.updated_at, updated_by=excluded.updated_by",
                (role, body.app_id, body.module_id, lvl, now, admin_user.get("email", "")),
            )
        conn.commit()

    log_action(
        request,
        module="settings",
        action="UPDATE",
        objet=f"role_default:{role}",
        detail=f"{body.app_id}/{body.module_id}: {prev_level or 'inherit'} → {lvl or 'inherit'}",
    )
    return {"ok": True, "role": role, "app_id": body.app_id, "module_id": body.module_id, "level": lvl or None}


@router.get("/api/settings/audit")
def get_audit_logs(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    module: str = "",
    action: str = "",
    search: str = "",
):
    require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
    from database import get_db
    import json
    with get_db() as conn:
        rows = conn.execute(
            """SELECT ff.id, ff.nom, ff.licence, ff.certificat, ff.has_fsc,
                      ff.traca_photo_url, ff.traca_explication, ff.traca_exemple_code,
                      ff.groupe, ff.branche,
                      ff.adresse, ff.code_postal, ff.ville, ff.pays,
                      ff.langue_default, ff.tags, ff.notes, ff.actif, ff.updated_at,
                      (SELECT COUNT(*) FROM fournisseur_contacts fc
                       WHERE fc.fournisseur_id = ff.id AND fc.actif=1) AS nb_contacts
               FROM fournisseurs_fsc ff
               ORDER BY ff.nom COLLATE NOCASE ASC"""
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        raw_tags = d.get("tags")
        if raw_tags:
            try:
                parsed = json.loads(raw_tags)
                d["tags"] = parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                d["tags"] = []
        else:
            d["tags"] = []
        out.append(d)
    return out


@router.get("/api/fournisseurs/groupes")
def list_fournisseurs_groupes(request: Request):
    """Liste des groupes distincts existants (pour autocomplete)."""
    require_settings(request)
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT groupe, COUNT(*) AS n FROM fournisseurs_fsc
               WHERE groupe IS NOT NULL AND TRIM(groupe) <> ''
               GROUP BY groupe COLLATE NOCASE
               ORDER BY groupe COLLATE NOCASE ASC"""
        ).fetchall()
    return [{"groupe": r["groupe"], "n": r["n"]} for r in rows]


def _parse_fournisseur_tags(raw):
    """Parse tags depuis body : accepte list JSON ou string séparée par virgules."""
    import json as _json
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        try:
            parsed = _json.loads(s)
            if isinstance(parsed, list):
                return [str(t).strip() for t in parsed if str(t).strip()]
        except (_json.JSONDecodeError, ValueError):
            pass
        return [t.strip() for t in s.split(",") if t.strip()]
    return []


def _normalize_langue_fournisseur(raw):
    v = (str(raw or "fr")).strip().lower()
    return v if v in ("fr", "en") else "fr"


@router.post("/api/fournisseurs")
async def create_fournisseur(request: Request):
    user = require_settings(request)
    from database import get_db
    import json
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    licence = (body.get("licence") or "").strip() or None
    certificat = (body.get("certificat") or "").strip() or None
    has_fsc = 1 if bool(body.get("has_fsc", True)) else 0
    if not has_fsc:
        licence = None
        certificat = None
    groupe = (body.get("groupe") or "").strip() or None
    branche = (body.get("branche") or "").strip() or None
    adresse = (body.get("adresse") or "").strip() or None
    code_postal = (body.get("code_postal") or "").strip() or None
    ville = (body.get("ville") or "").strip() or None
    pays = (body.get("pays") or "FR").strip() or "FR"
    langue_default = _normalize_langue_fournisseur(body.get("langue_default"))
    tags_list = _parse_fournisseur_tags(body.get("tags"))
    tags_json = json.dumps(tags_list, ensure_ascii=False) if tags_list else None
    notes = (body.get("notes") or "").strip() or None
    actif = 1 if bool(body.get("actif", True)) else 0
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du fournisseur requis")
    now = datetime.now().isoformat()
    with get_db() as conn:
        try:
            cur = conn.execute(
                """INSERT INTO fournisseurs_fsc
                   (nom, licence, certificat, has_fsc, groupe, branche,
                    adresse, code_postal, ville, pays, langue_default, tags,
                    notes, actif, updated_at)
                   VALUES (?,?,?,?,?,?, ?,?,?,?,?,?, ?,?,?)""",
                (nom, licence, certificat, has_fsc, groupe, branche,
                 adresse, code_postal, ville, pays, langue_default, tags_json,
                 notes, actif, now),
            )
            conn.commit()
            log_action(
                user=user,
                action="CREATE",
                module="settings",
                objet=f"Fournisseur {nom}",
                detail={"has_fsc": bool(has_fsc), "langue_default": langue_default,
                        "tags": tags_list, "ville": ville, "pays": pays,
                        "actif": bool(actif)},
                ip=request.client.host if request.client else None,
            )
            return {"success": True, "id": cur.lastrowid}
        except Exception:
            raise HTTPException(status_code=409, detail="Ce fournisseur existe déjà")


@router.put("/api/fournisseurs/{fournisseur_id}")
async def update_fournisseur(fournisseur_id: int, request: Request):
    user = require_settings(request)
    from database import get_db
    import json
    body = await request.json()
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        ex_cols = ex.keys()

        def _pick(field, default=None):
            if field in body:
                return body.get(field)
            return ex[field] if field in ex_cols else default

        nom = (body.get("nom") or ex["nom"] or "").strip()
        licence = _pick("licence")
        certificat = _pick("certificat")
        if isinstance(licence, str): licence = licence.strip() or None
        if isinstance(certificat, str): certificat = certificat.strip() or None
        if not nom:
            raise HTTPException(status_code=400, detail="Nom du fournisseur requis")
        try:
            has_fsc_prev = 1 if (ex["has_fsc"] if "has_fsc" in ex_cols else 1) else 0
        except Exception:
            has_fsc_prev = 1
        has_fsc = 1 if bool(body.get("has_fsc", has_fsc_prev)) else 0
        if not has_fsc:
            licence = None
            certificat = None
        traca_explication = (body.get("traca_explication") or "").strip() or None
        traca_exemple_code = (body.get("traca_exemple_code") or "").strip() or None
        groupe = _pick("groupe")
        branche = _pick("branche")
        if isinstance(groupe, str): groupe = groupe.strip() or None
        if isinstance(branche, str): branche = branche.strip() or None

        adresse = _pick("adresse")
        if isinstance(adresse, str): adresse = adresse.strip() or None
        code_postal = _pick("code_postal")
        if isinstance(code_postal, str): code_postal = code_postal.strip() or None
        ville = _pick("ville")
        if isinstance(ville, str): ville = ville.strip() or None
        pays = _pick("pays", "FR")
        if isinstance(pays, str): pays = pays.strip() or "FR"
        if "langue_default" in body:
            langue_default = _normalize_langue_fournisseur(body.get("langue_default"))
        else:
            langue_default = (ex["langue_default"] if "langue_default" in ex_cols else "fr") or "fr"
        if "tags" in body:
            tags_list = _parse_fournisseur_tags(body.get("tags"))
            tags_json = json.dumps(tags_list, ensure_ascii=False) if tags_list else None
        else:
            tags_json = ex["tags"] if "tags" in ex_cols else None
            try:
                tags_list = json.loads(tags_json) if tags_json else []
            except (json.JSONDecodeError, TypeError):
                tags_list = []
        notes = _pick("notes")
        if isinstance(notes, str): notes = notes.strip() or None
        actif_prev = int(ex["actif"] if "actif" in ex_cols and ex["actif"] is not None else 1)
        actif = 1 if bool(body.get("actif", actif_prev)) else 0

        now = datetime.now().isoformat()

        changed = {}
        _pairs = [
            ("nom", ex["nom"], nom),
            ("has_fsc", has_fsc_prev, has_fsc),
            ("langue_default", (ex["langue_default"] if "langue_default" in ex_cols else None), langue_default),
            ("ville", (ex["ville"] if "ville" in ex_cols else None), ville),
            ("actif", actif_prev, actif),
        ]
        for name, before, after in _pairs:
            if before != after:
                changed[name] = {"before": before, "after": after}

        try:
            conn.execute(
                """UPDATE fournisseurs_fsc SET
                       nom=?, licence=?, certificat=?, has_fsc=?,
                       traca_explication=?, traca_exemple_code=?, groupe=?, branche=?,
                       adresse=?, code_postal=?, ville=?, pays=?,
                       langue_default=?, tags=?, notes=?, actif=?, updated_at=?
                   WHERE id=?""",
                (nom, licence, certificat, has_fsc,
                 traca_explication, traca_exemple_code, groupe, branche,
                 adresse, code_postal, ville, pays,
                 langue_default, tags_json, notes, actif, now,
                 fournisseur_id),
            )
            conn.commit()
            log_action(
                user=user,
                action="UPDATE",
                module="settings",
                objet=f"Fournisseur {nom}",
                detail={"changed": changed, "tags": tags_list},
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
    user = require_settings(request)
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
    require_settings(request)
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
    for row in rows:
        d = dict(row)
        raw = d.pop("codes", None)
        d["items"] = raw.split("||") if raw else []
        result.append(d)
    return {"fournisseur": four["nom"], "receptions": result}


# ─── Fournisseurs : actif toggle + export CSV ─────────────────────

@router.patch("/api/fournisseurs/{fournisseur_id}/actif")
async def toggle_fournisseur_actif(fournisseur_id: int, request: Request):
    """Bascule / force le flag actif d'un fournisseur (soft archive)."""
    user = require_settings(request)
    from database import get_db
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    with get_db() as conn:
        ex = conn.execute("SELECT id, nom, actif FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        cur_actif = int(ex["actif"] if ex["actif"] is not None else 1)
        if "actif" in body:
            new_actif = 1 if bool(body.get("actif")) else 0
        else:
            new_actif = 0 if cur_actif else 1
        if new_actif == cur_actif:
            return {"success": True, "actif": bool(new_actif), "unchanged": True}
        conn.execute(
            "UPDATE fournisseurs_fsc SET actif=?, updated_at=? WHERE id=?",
            (new_actif, datetime.now().isoformat(), fournisseur_id),
        )
        conn.commit()
    log_action(
        user=user,
        action="UPDATE",
        module="settings",
        objet=f"Fournisseur {ex['nom']}",
        detail={"changed": {"actif": {"before": bool(cur_actif), "after": bool(new_actif)}}},
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "actif": bool(new_actif)}


@router.get("/api/fournisseurs/export.csv")
def export_fournisseurs_csv(request: Request):
    """Export CSV de la liste fournisseurs (colonnes principales + tags)."""
    from fastapi.responses import Response
    import csv, io, json as _json
    require_settings(request)
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT ff.id, ff.nom, ff.groupe, ff.branche, ff.has_fsc, ff.licence, ff.certificat,
                      ff.adresse, ff.code_postal, ff.ville, ff.pays,
                      ff.langue_default, ff.tags, ff.actif, ff.notes,
                      (SELECT COUNT(*) FROM fournisseur_contacts fc
                       WHERE fc.fournisseur_id=ff.id AND fc.actif=1) AS nb_contacts
               FROM fournisseurs_fsc ff
               ORDER BY ff.nom COLLATE NOCASE ASC"""
        ).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    w.writerow(["id", "nom", "groupe", "branche", "fsc", "licence", "certificat",
                "adresse", "code_postal", "ville", "pays",
                "langue", "tags", "actif", "notes", "nb_contacts"])
    for r in rows:
        tags_raw = r["tags"] or ""
        try:
            tags_parsed = _json.loads(tags_raw) if tags_raw else []
            tags_str = ", ".join(str(t) for t in tags_parsed) if isinstance(tags_parsed, list) else ""
        except (_json.JSONDecodeError, TypeError):
            tags_str = ""
        w.writerow([
            r["id"], r["nom"] or "", r["groupe"] or "", r["branche"] or "",
            "oui" if r["has_fsc"] else "non",
            r["licence"] or "", r["certificat"] or "",
            r["adresse"] or "", r["code_postal"] or "", r["ville"] or "", r["pays"] or "",
            (r["langue_default"] or "fr").upper(),
            tags_str, "oui" if (r["actif"] is None or r["actif"]) else "non",
            (r["notes"] or "").replace("\n", " "), r["nb_contacts"],
        ])
    log_action(
        user=require_settings(request),
        action="SEARCH",
        module="settings",
        objet=f"Export CSV fournisseurs ({len(rows)} lignes)",
        ip=request.client.host if request.client else None,
    )
    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="fournisseurs.csv"'},
    )


# ─── Fournisseur_contacts : CRUD contacts ──────────────────────────

def _row_contact_dict(row):
    import json as _json
    d = dict(row)
    for k in ("emails", "tels"):
        raw = d.get(k)
        if raw:
            try:
                parsed = _json.loads(raw)
                d[k] = parsed if isinstance(parsed, list) else []
            except (_json.JSONDecodeError, TypeError):
                d[k] = []
        else:
            d[k] = []
    d["is_principal"] = bool(d.get("is_principal"))
    d["actif"] = bool(d.get("actif")) if d.get("actif") is not None else True
    return d


def _parse_contact_list_field(raw):
    """Emails ou tels : accepte list JSON ou string séparée par virgules/points-virgules."""
    import json as _json
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(v).strip() for v in raw if str(v).strip()]
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        try:
            parsed = _json.loads(s)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except (_json.JSONDecodeError, ValueError):
            pass
        parts = [p.strip() for p in s.replace(";", ",").split(",")]
        return [p for p in parts if p]
    return []


def _unset_other_principal(conn, fournisseur_id: int, keep_contact_id: Optional[int]):
    """Assure qu'au plus un contact est is_principal=1 par fournisseur."""
    if keep_contact_id is None:
        conn.execute(
            "UPDATE fournisseur_contacts SET is_principal=0 WHERE fournisseur_id=?",
            (fournisseur_id,),
        )
    else:
        conn.execute(
            "UPDATE fournisseur_contacts SET is_principal=0 "
            "WHERE fournisseur_id=? AND id<>?",
            (fournisseur_id, keep_contact_id),
        )


@router.get("/api/fournisseurs/{fournisseur_id}/contacts")
def list_fournisseur_contacts(fournisseur_id: int, request: Request):
    require_settings(request)
    from database import get_db
    with get_db() as conn:
        ex = conn.execute("SELECT id, nom FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        rows = conn.execute(
            """SELECT * FROM fournisseur_contacts
               WHERE fournisseur_id=?
               ORDER BY is_principal DESC, actif DESC, nom COLLATE NOCASE ASC""",
            (fournisseur_id,),
        ).fetchall()
    return [_row_contact_dict(r) for r in rows]


@router.post("/api/fournisseurs/{fournisseur_id}/contacts")
async def create_fournisseur_contact(fournisseur_id: int, request: Request):
    user = require_settings(request)
    from database import get_db
    import json
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du contact requis")
    fonction = (body.get("fonction") or "").strip() or None
    emails_list = _parse_contact_list_field(body.get("emails"))
    tels_list = _parse_contact_list_field(body.get("tels"))
    emails_json = json.dumps(emails_list, ensure_ascii=False) if emails_list else None
    tels_json = json.dumps(tels_list, ensure_ascii=False) if tels_list else None
    langue = _normalize_langue_fournisseur(body.get("langue"))
    is_principal = 1 if bool(body.get("is_principal")) else 0
    actif = 1 if bool(body.get("actif", True)) else 0
    notes = (body.get("notes") or "").strip() or None
    now = datetime.now().isoformat()
    with get_db() as conn:
        ex = conn.execute("SELECT id, nom FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        cur = conn.execute(
            """INSERT INTO fournisseur_contacts
               (fournisseur_id, nom, fonction, emails, tels, langue,
                is_principal, actif, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?, ?,?,?,?,?)""",
            (fournisseur_id, nom, fonction, emails_json, tels_json, langue,
             is_principal, actif, notes, now, now),
        )
        new_id = cur.lastrowid
        if is_principal:
            _unset_other_principal(conn, fournisseur_id, new_id)
        conn.commit()
        row = conn.execute("SELECT * FROM fournisseur_contacts WHERE id=?", (new_id,)).fetchone()
    log_action(
        user=user,
        action="CREATE",
        module="settings",
        objet=f"Contact fournisseur {ex['nom']} · {nom}",
        detail={"emails": emails_list, "tels": tels_list, "langue": langue,
                "is_principal": bool(is_principal)},
        ip=request.client.host if request.client else None,
    )
    return _row_contact_dict(row)


@router.put("/api/fournisseurs/{fournisseur_id}/contacts/{contact_id}")
async def update_fournisseur_contact(fournisseur_id: int, contact_id: int, request: Request):
    user = require_settings(request)
    from database import get_db
    import json
    body = await request.json()
    with get_db() as conn:
        ex_four = conn.execute("SELECT id, nom FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not ex_four:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        ex = conn.execute(
            "SELECT * FROM fournisseur_contacts WHERE id=? AND fournisseur_id=?",
            (contact_id, fournisseur_id),
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Contact non trouvé")

        nom = (body.get("nom") or ex["nom"] or "").strip()
        if not nom:
            raise HTTPException(status_code=400, detail="Nom du contact requis")
        fonction = body.get("fonction") if "fonction" in body else ex["fonction"]
        if isinstance(fonction, str): fonction = fonction.strip() or None

        if "emails" in body:
            emails_list = _parse_contact_list_field(body.get("emails"))
            emails_json = json.dumps(emails_list, ensure_ascii=False) if emails_list else None
        else:
            emails_json = ex["emails"]
            try:
                emails_list = json.loads(emails_json) if emails_json else []
            except (json.JSONDecodeError, TypeError):
                emails_list = []

        if "tels" in body:
            tels_list = _parse_contact_list_field(body.get("tels"))
            tels_json = json.dumps(tels_list, ensure_ascii=False) if tels_list else None
        else:
            tels_json = ex["tels"]
            try:
                tels_list = json.loads(tels_json) if tels_json else []
            except (json.JSONDecodeError, TypeError):
                tels_list = []

        if "langue" in body:
            langue = _normalize_langue_fournisseur(body.get("langue"))
        else:
            langue = ex["langue"] or "fr"
        is_principal_prev = int(ex["is_principal"] or 0)
        is_principal = 1 if bool(body.get("is_principal", is_principal_prev)) else 0
        actif_prev = int(ex["actif"] if ex["actif"] is not None else 1)
        actif = 1 if bool(body.get("actif", actif_prev)) else 0
        notes = body.get("notes") if "notes" in body else ex["notes"]
        if isinstance(notes, str): notes = notes.strip() or None
        now = datetime.now().isoformat()

        conn.execute(
            """UPDATE fournisseur_contacts SET
                   nom=?, fonction=?, emails=?, tels=?, langue=?,
                   is_principal=?, actif=?, notes=?, updated_at=?
               WHERE id=? AND fournisseur_id=?""",
            (nom, fonction, emails_json, tels_json, langue,
             is_principal, actif, notes, now,
             contact_id, fournisseur_id),
        )
        if is_principal and not is_principal_prev:
            _unset_other_principal(conn, fournisseur_id, contact_id)
        conn.commit()
        row = conn.execute("SELECT * FROM fournisseur_contacts WHERE id=?", (contact_id,)).fetchone()
    log_action(
        user=user,
        action="UPDATE",
        module="settings",
        objet=f"Contact fournisseur {ex_four['nom']} · {nom}",
        detail={"emails": emails_list, "tels": tels_list, "langue": langue,
                "is_principal": bool(is_principal), "actif": bool(actif)},
        ip=request.client.host if request.client else None,
    )
    return _row_contact_dict(row)


@router.delete("/api/fournisseurs/{fournisseur_id}/contacts/{contact_id}")
def delete_fournisseur_contact(fournisseur_id: int, contact_id: int, request: Request):
    user = require_settings(request)
    from database import get_db
    with get_db() as conn:
        ex_four = conn.execute("SELECT nom FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not ex_four:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        ex = conn.execute(
            "SELECT nom FROM fournisseur_contacts WHERE id=? AND fournisseur_id=?",
            (contact_id, fournisseur_id),
        ).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Contact non trouvé")
        conn.execute("DELETE FROM fournisseur_contacts WHERE id=? AND fournisseur_id=?",
                     (contact_id, fournisseur_id))
        conn.commit()
    log_action(
        user=user,
        action="DELETE",
        module="settings",
        objet=f"Contact fournisseur {ex_four['nom']} · {ex['nom']}",
        ip=request.client.host if request.client else None,
    )
    return {"success": True}


# ─── Annonces de mise à jour ──────────────────────────────

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
    require_settings(request)
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
    require_settings(request)
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
    user = require_settings(request)
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
    require_settings(request)
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
    user = require_settings(request)
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
    require_settings(request)
    from database import get_db
    from app.services.operations_config import categories_for_ui, list_operation_codes as _list

    with get_db() as conn:
        items = _list(conn)
    return {"items": items, "categories": categories_for_ui()}


@router.post("/api/settings/operation-codes")
async def create_operation_code(request: Request):
    require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
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
    user = require_settings(request)
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
    user = require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
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
    require_settings(request)
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
    """Lit APP_VERSION dans config.py côté origin/staging (ce qui sera promu).
    Le script promote_v2.sh merge staging → main automatiquement avant le reset v2."""
    try:
        out = _subprocess.check_output(
            [_GIT_BIN, "-C", V2_REPO_PATH, "show", "origin/staging:config.py"],
            text=True, timeout=10,
        )
        return _parse_version_from_text(out)
    except Exception:
        return None


@router.get("/api/promote/status")
def promote_status(request: Request):
    require_settings(request)

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
        # On compare contre origin/staging : c'est ce qui sera réellement promu
        # (le script promote_v2.sh merge staging → main avant le reset v2).
        origin_ref = _subprocess.check_output(
            [_GIT_BIN, "-C", V2_REPO_PATH, "rev-parse", "origin/staging"],
            text=True, timeout=5,
        ).strip()
    except Exception as exc:
        raise HTTPException(500, f"Lecture git impossible : {exc}")

    v2_version = _read_v2_app_version()
    next_version = _read_origin_app_version() or v2_version

    commits_ahead = []
    if v2_head != origin_ref:
        try:
            log_out = _subprocess.check_output(
                [_GIT_BIN, "-C", V2_REPO_PATH, "log",
                 f"{v2_head}..{origin_ref}",
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
        "origin_head": origin_ref[:7],
        "commits_ahead": commits_ahead,
        "can_promote": can_promote,
        "reason": reason,
    }


@router.post("/api/promote")
async def promote_run(request: Request):
    require_settings(request)
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


# ─── Sync DB v2 → v1 ───────────────────────────────────────────────────────────
# Recopie la base de production (v2) vers v1 en utilisant le script existant
# /usr/local/bin/mysifa-v1-resync-db.sh (déjà installé pour le cron nightly).
# Le script fait : stop v1, sqlite3 .backup (live-safe) v2 → v1, restart v1,
# healthcheck. Backups pré-resync tournés dans /home/sifa/backups/v1-db-rotation/.
#
# IMPORTANT : le script stoppe v1 au début. S'il est lancé directement depuis
# le process v1 (via subprocess), systemd tue toute la cgroup du service et le
# script se fait tuer avant d'atteindre le restart. On le lance donc en détaché
# via `systemd-run --no-block` qui crée une nouvelle cgroup indépendante.
RESYNC_SCRIPT = "/usr/local/bin/mysifa-v1-resync-db.sh"
# systemd lance le service avec un PATH minimal qui ne contient pas /usr/bin :
# on résout sudo et systemd-run une fois au boot avec un PATH explicite.
_SUDO_BIN = _shutil.which("sudo", path="/usr/bin:/bin:/usr/local/bin") or "/usr/bin/sudo"
_SYSTEMD_RUN_BIN = _shutil.which("systemd-run", path="/usr/bin:/bin:/usr/local/bin") or "/usr/bin/systemd-run"


@router.post("/api/sync-db-v1")
async def sync_db_v1(request: Request):
    require_settings(request)
    try:
        # systemd-run --no-block lance le script dans une unite transitoire
        # detachee qui survit a l'arret de mysifa-v1. Retour quasi-instantane.
        proc = await asyncio.create_subprocess_exec(
            _SUDO_BIN, "-n",
            _SYSTEMD_RUN_BIN,
            "--unit=mysifa-v1-resync-oneshot",
            "--collect",
            "--no-block",
            RESYNC_SCRIPT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out_bytes, _ = await proc.communicate()
        out = (out_bytes or b"").decode("utf-8", errors="replace")
        if proc.returncode != 0:
            raise HTTPException(
                500,
                f"Impossible de lancer la resync (code {proc.returncode}).\n\n{out[-2000:]}",
            )
        return {
            "ok": True,
            "output": out[-2000:],
            "message": "Resync lancee. v1 sera indisponible 10-20s puis redemarrera automatiquement.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Impossible de lancer le script de resync : {exc}")


# ─── Codes maintenance (CRUD) ──────────────────────────────────────────────────
# Référentiel des codes d'opérations de maintenance, stockés en base SQLite
# (anciennement localStorage côté navigateur). Migrés via la migration v128.
# Endpoints super admin uniquement (cohérent avec les autres référentiels settings).


def _require_maint_writer(request: Request) -> dict:
    """Édition des codes maintenance : super admin, direction, administration."""
    user = get_current_user(request)
    if user.get("role") not in ROLES_ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")
    return user


def _maint_row_to_dict(r) -> dict:
    # PRAGMA table_info dynamique : intervalle / metrage_ref peuvent être absents
    # sur les vieilles DB qui n'ont pas encore joué les migrations v129 / v131.
    try:
        intervalle = r["intervalle"]
    except (IndexError, KeyError):
        intervalle = None
    try:
        metrage_ref = r["metrage_ref"]
    except (IndexError, KeyError):
        metrage_ref = None
    # v180 : libre + usage_count (fallback safe pour DB pas encore migree).
    try:
        libre_v = bool(r["libre"])
    except (IndexError, KeyError):
        libre_v = False
    try:
        usage_v = int(r["usage_count"] or 0)
    except (IndexError, KeyError, TypeError, ValueError):
        usage_v = 0
    return {
        "code": r["code"],
        "label": r["label"],
        "niveau": int(r["niveau"] or 1),
        "categorie": r["categorie"] or "controles",
        "periodique": bool(r["periodique"]),
        "intervalle": intervalle or "",
        "metrage_ref": metrage_ref or "",
        "libre": libre_v,
        "usage_count": usage_v,
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


def _normalize_maint_payload(body: dict) -> dict:
    code = (body.get("code") or "").strip()
    label = (body.get("label") or "").strip()
    try:
        niveau = int(body.get("niveau") or 1)
    except (TypeError, ValueError):
        niveau = 1
    if niveau < 1 or niveau > 3:
        raise HTTPException(422, "Niveau invalide (1-3).")
    categorie = (body.get("categorie") or "controles").strip()
    # Depuis v178, "interventions" est scindée en "entretien" et "remplacements".
    # Les valeurs legacy ("interventions", "suivi") sont normalisées vers "entretien".
    if categorie not in ("controles", "entretien", "remplacements", "interventions", "suivi"):
        categorie = "controles"
    if categorie in ("interventions", "suivi"):
        categorie = "entretien"
    # v2.2.17 — Le concept de "périodique" a été retiré côté UI. Tous les
    # codes sont considérés comme périodiques (periodique=1 forcé), quelle
    # que soit la valeur envoyée par le client (compat legacy).
    periodique = 1
    intervalle = (body.get("intervalle") or "").strip()
    if len(intervalle) > 80:
        intervalle = intervalle[:80]
    # Référence métrage : texte libre (ex. "5000 m"), surtout utile pour la
    # catégorie "Suivi" (pièces d'usure). On le garde sur les autres catégories
    # si l'utilisateur le saisit, mais il sera ignoré par l'UI consommatrice.
    metrage_ref = (body.get("metrage_ref") or "").strip()
    if len(metrage_ref) > 80:
        metrage_ref = metrage_ref[:80]
    if not code:
        raise HTTPException(422, "Code obligatoire.")
    if not label:
        raise HTTPException(422, "Libelle obligatoire.")
    return {
        "code": code,
        "label": label,
        "niveau": niveau,
        "categorie": categorie,
        "periodique": periodique,
        "intervalle": intervalle,
        "metrage_ref": metrage_ref,
    }


_ALERT_PLACEMENTS = {"center", "top-right", "bottom-right"}
# Anciennes valeurs acceptées en lecture (legacy) — normalisées vers "center"
_ALERT_PLACEMENTS_LEGACY = {"top", "bottom"}
_ALERT_STACK_MODES = {"stack", "queue", "replace"}
_ALERT_MIN_INTERVAL_MINUTES = 1
_ALERT_MAX_INTERVAL_MINUTES = 7 * 24 * 60  # 7 jours
# Délai d'attente après une "reprise de production" avant qu'une alerte
# périodique puisse se déclencher (constante, non paramétrable).
ALERT_RESUME_GRACE_MINUTES = 5
_ALERT_SIZES = {"small", "medium", "large"}
_ALERT_TRIGGER_TYPES = {"manual", "periodic", "calendar", "event"}
_ALERT_TRIGGER_EVENTS = {"dossier_start", "dossier_end", "machine_change", "login", "after_calage"}
_ALERT_CALENDAR_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


def operator_should_see_alert(
    user_role: str,
    user_machine: str,
    target: dict,
) -> bool:
    """Filtre opérateur : doit-on afficher cette alerte à cet utilisateur ?

    Règles (figées) :
    - Le super administrateur voit toujours toutes les alertes (test +
      monitoring).
    - Sinon, seuls les opérateurs `fabrication` voient les alertes. Tout
      autre rôle est exclu (pas de configuration utilisateur de ce filtre).
    - target["machines"] est une liste : si elle contient "*", l'alerte
      vaut pour toutes les machines ; sinon, la machine actuellement
      ouverte par l'opérateur doit y figurer.

    Cette fonction sera importée par le futur endpoint qui retourne les
    alertes actives à pousser sur l'écran de l'opérateur.
    """
    if user_role == ROLE_SUPERADMIN:
        return True
    if user_role != ROLE_FABRICATION:
        return False
    machines = (target or {}).get("machines")
    if not isinstance(machines, list) or not machines:
        # Compat : ancien format avec target["machine"] string
        legacy = (target or {}).get("machine")
        machines = [legacy] if isinstance(legacy, str) and legacy else ["*"]
    if "*" in machines:
        return True
    if not user_machine:
        return False
    return user_machine in machines


def _validate_alert_params(params: dict) -> dict:
    """Valide et normalise les paramètres d'une alerte (déclencheur, cible,
    validation). Retourne un dict propre prêt à être stocké en JSON. Accepte
    un dict vide (valeurs par défaut)."""
    if not isinstance(params, dict):
        raise HTTPException(422, "params doit être un objet JSON.")
    out = {}

    # description : contexte affiche a l'operateur au moment du declenchement.
    # Optionnelle, plafonnee a 800 caracteres pour rester lisible.
    desc_in = params.get("description")
    if isinstance(desc_in, str):
        desc_clean = desc_in.strip()[:800]
        if desc_clean:
            out["description"] = desc_clean

    # trigger
    trig_in = params.get("trigger") or {}
    if not isinstance(trig_in, dict):
        raise HTTPException(422, "trigger doit être un objet.")
    t_type = (trig_in.get("type") or "manual").strip()
    if t_type not in _ALERT_TRIGGER_TYPES:
        raise HTTPException(422, f"Déclencheur inconnu : {t_type!r}.")
    trig = {"type": t_type}
    if t_type == "periodic":
        # On accepte interval_minutes (canonique) ou interval_hours (compat
        # rétro). Le stockage est toujours en minutes.
        minutes_raw = trig_in.get("interval_minutes")
        if minutes_raw is None and trig_in.get("interval_hours") is not None:
            try:
                minutes_raw = float(trig_in.get("interval_hours")) * 60.0
            except (TypeError, ValueError):
                minutes_raw = None
        try:
            minutes = int(round(float(minutes_raw)))
        except (TypeError, ValueError):
            raise HTTPException(422, "interval_minutes invalide.")
        if minutes < _ALERT_MIN_INTERVAL_MINUTES or minutes > _ALERT_MAX_INTERVAL_MINUTES:
            raise HTTPException(
                422,
                f"interval_minutes hors plage ({_ALERT_MIN_INTERVAL_MINUTES} <= n <= {_ALERT_MAX_INTERVAL_MINUTES}).",
            )
        trig["interval_minutes"] = minutes
        # grace_minutes : délai avant la première alerte de chaque session
        # (par défaut = ALERT_RESUME_GRACE_MINUTES = 5). Personnalisable par
        # alerte pour espacer naturellement les premières alertes des
        # différents contrôles au démarrage d'une session.
        grace_raw = trig_in.get("grace_minutes")
        if grace_raw is None:
            grace_val = ALERT_RESUME_GRACE_MINUTES
        else:
            try:
                grace_val = int(round(float(grace_raw)))
            except (TypeError, ValueError):
                grace_val = ALERT_RESUME_GRACE_MINUTES
        if grace_val < 0:
            grace_val = 0
        if grace_val > 120:
            grace_val = 120
        trig["grace_minutes"] = grace_val
        # Sémantique du déclenchement (documentée pour le futur planificateur) :
        #   - Le compteur de N minutes démarre après une saisie "production"
        #     (ou "reprise de production") sur la machine cible.
        #   - Si la machine n'est plus en production, l'alerte est différée
        #     jusqu'à une "reprise de production", puis un délai de
        #     ALERT_RESUME_GRACE_MINUTES minutes (5) est respecté avant
        #     déclenchement.
        #   - Après validation par l'opérateur, le compteur N redémarre dans
        #     les mêmes conditions.
    elif t_type == "calendar":
        time = (trig_in.get("time") or "").strip()
        # HH:MM
        try:
            hh, mm = time.split(":")
            assert 0 <= int(hh) < 24 and 0 <= int(mm) < 60
        except (ValueError, AssertionError):
            raise HTTPException(422, "time doit être au format HH:MM.")
        trig["time"] = f"{int(hh):02d}:{int(mm):02d}"
        days = trig_in.get("days") or []
        if not isinstance(days, list) or not days:
            days = list(_ALERT_CALENDAR_DAYS)
        bad = [d for d in days if d not in _ALERT_CALENDAR_DAYS]
        if bad:
            raise HTTPException(422, f"days invalides : {bad}.")
        # Conserver l'ordre canonique de la semaine
        order = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        trig["days"] = [d for d in order if d in days]
    elif t_type == "event":
        ev = (trig_in.get("event") or "").strip()
        if ev not in _ALERT_TRIGGER_EVENTS:
            raise HTTPException(422, f"event inconnu : {ev!r}.")
        trig["event"] = ev
        # v163+ : filtre produit (bobine/plis) — appliqué uniquement pour
        # les événements liés à un dossier. Silencieusement ignoré pour
        # les autres événements (machine_change, login…).
        if ev in ("dossier_start", "dossier_end"):
            fc = (trig_in.get("filter_conditionnement") or "").strip()
            if fc in ("bobine_only", "plis_only"):
                trig["filter_conditionnement"] = fc
            # 'any' ou absent : on n'écrit rien (comportement par défaut).
        # v2.2.79 : délai en minutes pour after_calage (temps en prod cumulé)
        if ev == "after_calage":
            _delay_raw = trig_in.get("delay_minutes", 0)
            try:
                _delay = int(_delay_raw) if _delay_raw not in (None, "") else 0
            except (TypeError, ValueError):
                _delay = 0
            if _delay < 0:
                _delay = 0
            if _delay > 999:
                _delay = 999
            trig["delay_minutes"] = _delay
    # type=manual : pas de params supplémentaires
    out["trigger"] = trig

    # target — multi-machines, sans rôle (les opérateurs fabrication + le
    # super admin voient toujours, c'est figé côté code).
    tgt_in = params.get("target") or {}
    if not isinstance(tgt_in, dict):
        raise HTTPException(422, "target doit être un objet.")
    machines_in = tgt_in.get("machines")
    if machines_in is None:
        # Compat : ancien champ "machine" (string)
        legacy = tgt_in.get("machine")
        if isinstance(legacy, str) and legacy.strip():
            machines_in = [legacy.strip()]
        else:
            machines_in = ["*"]
    if not isinstance(machines_in, list):
        raise HTTPException(422, "target.machines doit être une liste.")
    clean_machines = []
    seen = set()
    for m in machines_in:
        if not isinstance(m, str):
            continue
        s = m.strip()[:80]
        if s and s not in seen:
            clean_machines.append(s)
            seen.add(s)
    if not clean_machines:
        clean_machines = ["*"]
    if "*" in clean_machines:
        # Wildcard absorbe le reste pour éviter les listes redondantes.
        clean_machines = ["*"]
    out["target"] = {"machines": clean_machines}

    # validation
    val_in = params.get("validation") or {}
    if not isinstance(val_in, dict):
        raise HTTPException(422, "validation doit être un objet.")
    btn = (val_in.get("button_label") or "Valider").strip() or "Valider"
    if len(btn) > 40:
        btn = btn[:40]
    out["validation"] = {"button_label": btn}

    # v2.2.88 : block_production par alerte (défaut False). Quand True,
    # la modale s'affiche avec backdrop bloquant et le backend refuse toute
    # saisie de production tant que l'alerte n'est pas ack.
    out["block_production"] = bool(params.get("block_production", False))

    # v164+ : bouton "Fermer l'alerte" configurable. Permet à l'opérateur
    # d'esquiver une alerte non pertinente sans polluer l'historique. Aucune
    # trace : simple dismiss silencieux qui débloque juste le prochain trigger.
    dismiss_in = params.get("dismiss_button") or {}
    if isinstance(dismiss_in, dict):
        d_enabled = bool(dismiss_in.get("enabled"))
        d_label = (dismiss_in.get("label") or "Fermer l'alerte").strip() or "Fermer l'alerte"
        if len(d_label) > 40:
            d_label = d_label[:40]
        if d_enabled:
            out["dismiss_button"] = {"enabled": True, "label": d_label}

    # checklist (questionnaire) : liste de points de contrôle que l'opérateur
    # cochera lors de la validation. Items = chaînes libres (ex. "Découpe nette",
    # "Colle conforme"). L'opérateur peut valider même partiellement rempli
    # (une confirmation lui est demandée dans ce cas, sans blocage).
    cl_in = params.get("checklist") or {}
    if not isinstance(cl_in, dict):
        raise HTTPException(422, "checklist doit être un objet.")
    cl_enabled = bool(cl_in.get("enabled"))
    items_in = cl_in.get("items") or []
    if not isinstance(items_in, list):
        raise HTTPException(422, "checklist.items doit être une liste.")
    clean_items = []
    for it in items_in:
        # Compat : ancienne forme = string
        if isinstance(it, str):
            label = it.strip()[:200]
            if label:
                clean_items.append({"type": "choice", "label": label,
                                    "responses": ["Conforme"]})
            continue
        if not isinstance(it, dict):
            continue
        label = (it.get("label") or "").strip()[:200]
        if not label:
            continue
        item_type = (it.get("type") or "choice").strip()
        if item_type not in ("choice", "value"):
            item_type = "choice"
        if item_type == "value":
            # Saisie d'une valeur numérique (pression, température, dimension…)
            unit = (it.get("unit") or "").strip()[:20]
            def _f(x):
                if x is None or x == "":
                    return None
                try:
                    return float(x)
                except (TypeError, ValueError):
                    return None
            vmin = _f(it.get("min"))
            vmax = _f(it.get("max"))
            # Robustesse : si min > max, on échange plutôt que de planter.
            if vmin is not None and vmax is not None and vmin > vmax:
                vmin, vmax = vmax, vmin
            item_out = {"type": "value", "label": label}
            if unit:
                item_out["unit"] = unit
            if vmin is not None:
                item_out["min"] = vmin
            if vmax is not None:
                item_out["max"] = vmax
            # v2.2.85 : required (bool). Défaut false (optionnel = rétro-compat).
            if bool(it.get("required", False)):
                item_out["required"] = True
            clean_items.append(item_out)
            continue
        # type "choice" (cases à cocher)
        responses_in = it.get("responses") or []
        if not isinstance(responses_in, list):
            continue
        clean_responses = []
        seen = set()
        for r in responses_in:
            if not isinstance(r, str):
                continue
            rs = r.strip()[:100]
            if rs and rs not in seen:
                clean_responses.append(rs)
                seen.add(rs)
        if len(clean_responses) > 20:
            clean_responses = clean_responses[:20]
        if not clean_responses:
            clean_responses = ["Conforme"]
        # multi : si true, l'opérateur peut cocher plusieurs réponses
        # (checkboxes). Si false, une seule réponse possible (radio).
        # Défaut true pour préserver le comportement des alertes existantes.
        multi = bool(it.get("multi", True))
        # allow_other : si true, l'opérateur voit une case "Autre" en plus des
        # réponses configurées, et peut compléter avec une explication libre
        # (stockée dans responses["<idx>_other"] lors de l'ack).
        allow_other = bool(it.get("allow_other", False))
        # other_is_nc : si true (uniquement pertinent quand allow_other), la
        # sélection de "Autre" par l'opérateur marque la ligne comme non
        # conforme dans l'historique, au même titre qu'une entrée de
        # nc_responses.
        other_is_nc = bool(it.get("other_is_nc", False)) and allow_other
        # nc_responses : sous-ensemble des réponses proposées qui, lorsqu'elles
        # sont cochées par l'opérateur, marquent la ligne d'ack comme "non
        # conforme" dans l'historique. Défini librement par l'admin lors de la
        # création / modification de l'alerte.
        nc_in = it.get("nc_responses") or []
        clean_nc = []
        if isinstance(nc_in, list):
            seen_r_set = set(clean_responses)
            seen_nc = set()
            for r in nc_in:
                if not isinstance(r, str):
                    continue
                rs = r.strip()[:100]
                if rs and rs in seen_r_set and rs not in seen_nc:
                    clean_nc.append(rs)
                    seen_nc.add(rs)
        # v2.2.85 : required (bool). Défaut false.
        required_choice = bool(it.get("required", False))
        _choice_item = {"type": "choice", "label": label,
                        "responses": clean_responses, "multi": multi,
                        "allow_other": allow_other,
                        "other_is_nc": other_is_nc,
                        "nc_responses": clean_nc}
        if required_choice:
            _choice_item["required"] = True
        clean_items.append(_choice_item)
    if len(clean_items) > 30:
        raise HTTPException(422, "checklist.items : 30 points maximum.")
    if cl_enabled and not clean_items:
        cl_enabled = False
    # all_required retiré (UX) : le mode opérateur affiche une confirmation
    # quand le formulaire n'est pas entièrement rempli, sans bloquer.
    out["checklist"] = {
        "enabled": cl_enabled,
        "items": clean_items,
    }

    # comment_enabled : toujours True en v1 (mais on stocke pour l'avenir)
    out["comment_enabled"] = True

    return out


def _require_alerts_admin_module(request: Request) -> dict:
    # Alias local pour clarté dans les nouveaux endpoints
    return _require_alerts_admin(request)


def _alert_nom_for_code(code: str, label: str) -> str:
    """Convention de nommage des alertes auto-générées."""
    label = (label or "").strip()
    nom = f"Contrôle : {code} – {label}" if label else f"Contrôle : {code}"
    return nom[:120]


def _is_non_periodic_control(categorie: str, periodique) -> bool:
    # v2.2.15 — Le concept de "contrôle non périodique" a été retiré. Cette
    # fonction retourne toujours False pour neutraliser toute logique legacy
    # qui l'appellerait encore. Migration 189 a converti les codes existants.
    return False


def _sync_alert_for_code(conn, code: str, label: str, categorie: str, periodique, now: str) -> None:
    """v2.2.15 — No-op. Le système d'alertes automatiques liées aux codes de
    contrôle non périodique a été retiré (migration 189). Fonction gardée
    pour ne pas casser les callers legacy — les alertes sont désormais 100%
    manuelles via l'UI Paramètres → Alertes.
    """
    return


@router.get("/api/maintenance/codes")
def maintenance_codes_list(request: Request, include_libres: int = 0):
    """Liste des codes maintenance du catalogue standard.
    Depuis v180, les codes libres (libre=1) sont exclus par defaut. Pour les
    inclure (ex. panneau admin dedié), passer include_libres=1.
    """
    get_current_user(request)
    from database import get_db
    with get_db() as conn:
        # SELECT defensif : libre + usage_count peuvent ne pas exister sur
        # DB pas encore migree. Le try/except dans _maint_row_to_dict
        # gere le fallback.
        cols = {c["name"] for c in conn.execute("PRAGMA table_info(maintenance_codes)").fetchall()}
        has_libre = "libre" in cols
        has_usage = "usage_count" in cols
        sel_extra = ""
        if has_libre: sel_extra += ",libre"
        if has_usage: sel_extra += ",usage_count"
        where = ""
        if has_libre and not include_libres:
            where = "WHERE libre = 0"
        rows = conn.execute(
            f"""SELECT code,label,niveau,categorie,periodique,intervalle,metrage_ref,
                      created_at,updated_at{sel_extra}
               FROM maintenance_codes
               {where}
               ORDER BY categorie ASC, code ASC"""
        ).fetchall()
        # Enrichissement : nombre de documents attaches par code
        # (Table creee a la volee si absente, garantit la robustesse).
        docs_by_code = {}
        try:
            _ensure_maint_docs_table(conn)
            drows = conn.execute(
                "SELECT code, COUNT(*) AS n FROM maintenance_docs GROUP BY code"
            ).fetchall()
            for dr in drows:
                docs_by_code[dr["code"]] = int(dr["n"])
        except Exception:
            docs_by_code = {}
    items = []
    for r in rows:
        d = _maint_row_to_dict(r)
        d["docs_count"] = docs_by_code.get(d["code"], 0)
        items.append(d)
    return {"items": items}


@router.post("/api/maintenance/codes")
async def maintenance_codes_create(request: Request):
    user = _require_maint_writer(request)
    body = await request.json()
    data = _normalize_maint_payload(body)
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        existing = conn.execute(
            "SELECT 1 FROM maintenance_codes WHERE code=? LIMIT 1", (data["code"],)
        ).fetchone()
        if existing:
            raise HTTPException(409, f"Le code {data['code']} existe deja.")
        conn.execute(
            """INSERT INTO maintenance_codes
               (code,label,niveau,categorie,periodique,intervalle,metrage_ref,
                created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (data["code"], data["label"], data["niveau"], data["categorie"],
             data["periodique"], data["intervalle"], data["metrage_ref"], now, now),
        )
        _sync_alert_for_code(conn, data["code"], data["label"],
                             data["categorie"], data["periodique"], now)
        conn.commit()
    log_action(user=user, action="CREATE", module="maintenance_codes",
               objet=data["code"], detail=data["label"])
    return {"ok": True, "code": data["code"]}


@router.put("/api/maintenance/codes/{code}")
async def maintenance_codes_update(code: str, request: Request):
    user = _require_maint_writer(request)
    body = await request.json()
    # On force le code de l'URL (immuable apres creation)
    body["code"] = code
    data = _normalize_maint_payload(body)
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE maintenance_codes
               SET label=?, niveau=?, categorie=?, periodique=?, intervalle=?,
                   metrage_ref=?, updated_at=?
               WHERE code=?""",
            (data["label"], data["niveau"], data["categorie"],
             data["periodique"], data["intervalle"], data["metrage_ref"], now, data["code"]),
        )
        if cur.rowcount == 0:
            conn.rollback()
            raise HTTPException(404, f"Code {code} introuvable.")
        _sync_alert_for_code(conn, data["code"], data["label"],
                             data["categorie"], data["periodique"], now)
        conn.commit()
    log_action(user=user, action="UPDATE", module="maintenance_codes",
               objet=data["code"], detail=data["label"])
    return {"ok": True, "code": data["code"]}


@router.delete("/api/maintenance/codes/{code}")
def maintenance_codes_delete(code: str, request: Request):
    user = _require_maint_writer(request)
    from database import get_db
    with get_db() as conn:
        cur = conn.execute("DELETE FROM maintenance_codes WHERE code=?", (code,))
        if cur.rowcount == 0:
            conn.rollback()
            raise HTTPException(404, f"Code {code} introuvable.")
        # v2.2.15 — Plus de cascade sur les alertes (le système auto a été
        # retiré). Les alertes classiques (manuelles) ne sont jamais liées
        # à un code, donc rien à supprimer côté maintenance_alerts.
        conn.commit()
    log_action(user=user, action="DELETE", module="maintenance_codes",
               objet=code, detail="")
    return {"ok": True}


class _MaintBulkImport(BaseModel):
    items: list


@router.post("/api/maintenance/codes/bulk-import")
async def maintenance_codes_bulk_import(request: Request):
    """Import en masse depuis le localStorage du navigateur (migration one-shot).
    N'ecrase pas les codes existants : INSERT OR IGNORE.
    """
    user = _require_maint_writer(request)
    body = await request.json()
    items = body.get("items") or []
    if not isinstance(items, list):
        raise HTTPException(422, "Format invalide : 'items' doit etre une liste.")
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    imported = 0
    with get_db() as conn:
        for raw in items:
            if not isinstance(raw, dict):
                continue
            try:
                data = _normalize_maint_payload(raw)
            except HTTPException:
                continue
            cur = conn.execute(
                """INSERT OR IGNORE INTO maintenance_codes
                   (code,label,niveau,categorie,periodique,intervalle,metrage_ref,
                    created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (data["code"], data["label"], data["niveau"], data["categorie"],
                 data["periodique"], data["intervalle"], data["metrage_ref"],
                 raw.get("created_at") or now, now),
            )
            if cur.rowcount:
                imported += 1
                _sync_alert_for_code(conn, data["code"], data["label"],
                                     data["categorie"], data["periodique"], now)
        conn.commit()
    log_action(user=user, action="IMPORT", module="maintenance_codes",
               objet="bulk", detail=f"{imported} codes")
    return {"ok": True, "imported": imported, "received": len(items)}


# ── Documents attaches aux codes maintenance ───────────────────────────────
# Fichiers explicatifs (PDF, images, videos, etc.) uploades pour chaque code
# de maintenance. Consultes par les operateurs depuis /maintenance quand ils
# executent le controle ou l'intervention correspondante.

_MAINT_DOCS_SUBDIR = "data/uploads/maintenance_docs"
_MAINT_DOCS_MAX_BYTES = 20 * 1024 * 1024  # 20 Mo


def _ensure_maint_docs_table(conn) -> None:
    """Garantit la presence de la table maintenance_docs. Ceinture + bretelles :
    si la migration v149 n'a pas tourne (parce que v1 n'a pas encore restart,
    ou parce qu'une migration precedente a plante), on cree la table ici.
    Idempotent grace au CREATE TABLE IF NOT EXISTS."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS maintenance_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            size_bytes INTEGER,
            content_type TEXT,
            uploaded_by TEXT,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY (code) REFERENCES maintenance_codes(code) ON DELETE CASCADE
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_maint_docs_code ON maintenance_docs(code)")


def _maint_docs_dir(code: str) -> Path:
    d = Path(BASE_DIR) / _MAINT_DOCS_SUBDIR / code
    d.mkdir(parents=True, exist_ok=True)
    return d


def _maint_safe_filename(name: str) -> str:
    import re as _re
    import unicodedata as _ud
    name = _ud.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii")
    name = _re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    return name or "fichier"


# ─── Endpoints Interventions libres (v180) ─────────────────────────
# Interventions ponctuelles saisies par l'operateur sans creer de code du
# catalogue. Chaque titre libre devient un code technique LIB-xxxxxx en
# base, exclu du catalogue standard (voir maintenance_codes_list).

def _next_libre_code(conn) -> str:
    """Genere le prochain identifiant LIB-000042. Format numerique sequentiel
    sur 6 chiffres, base sur MAX(code) existant."""
    row = conn.execute(
        "SELECT code FROM maintenance_codes WHERE libre=1 AND code LIKE 'LIB-%' "
        "ORDER BY code DESC LIMIT 1"
    ).fetchone()
    if not row:
        return "LIB-000001"
    try:
        n = int((row["code"] or "").split("-", 1)[1]) + 1
    except (ValueError, IndexError):
        n = 1
    return f"LIB-{n:06d}"


@router.get("/api/maintenance/codes/libres/autocomplete")
def maintenance_libres_autocomplete(request: Request, q: str = "", limit: int = 10):
    """Autocomplete sur les titres des interventions libres deja saisies.
    Tri par pertinence : usage_count DESC, puis updated_at DESC.
    v182bis : try/except global pour surfacer l'erreur reelle dans les logs et
    ne jamais bloquer la saisie utilisateur (retour {items: []} en cas d'erreur).
    """
    try:
        get_current_user(request)
        from database import get_db
        q_norm = (q or "").strip()
        if len(q_norm) < 1:
            return {"items": []}
        limit_v = max(1, min(int(limit or 10), 50))
        like = f"%{q_norm}%"
        with get_db() as conn:
            cols = {c["name"] for c in conn.execute("PRAGMA table_info(maintenance_codes)").fetchall()}
            if "libre" not in cols:
                return {"items": []}
            has_usage = "usage_count" in cols
            if has_usage:
                sql = ("SELECT code, label, niveau, categorie, usage_count "
                       "FROM maintenance_codes "
                       "WHERE libre = 1 AND label LIKE ? "
                       "ORDER BY usage_count DESC, updated_at DESC, code DESC "
                       "LIMIT ?")
            else:
                sql = ("SELECT code, label, niveau, categorie, 0 AS usage_count "
                       "FROM maintenance_codes "
                       "WHERE libre = 1 AND label LIKE ? "
                       "ORDER BY updated_at DESC, code DESC "
                       "LIMIT ?")
            rows = conn.execute(sql, (like, limit_v)).fetchall()
        items = []
        for r in rows:
            try:
                items.append({
                    "code": r["code"],
                    "label": r["label"],
                    "niveau": int(r["niveau"] or 1),
                    "categorie": r["categorie"] or "remplacements",
                    "usage_count": int(r["usage_count"] or 0),
                })
            except Exception:
                continue
        return {"items": items}
    except HTTPException:
        raise
    except Exception as e:
        import logging, traceback
        logging.error("libres autocomplete FAIL: %s\n%s", e, traceback.format_exc())
        # Ne bloque pas l'user : retourne liste vide, l'erreur est loggee
        return {"items": [], "error": str(e)}


@router.post("/api/maintenance/codes/libres")
async def maintenance_libres_create(request: Request):
    """Cree un code libre a la volee. Body : {label, categorie?, niveau?}.
    Le code technique (LIB-xxx) est genere par le serveur, jamais fourni par
    l'operateur. Les defauts sont categorie=remplacements, niveau=1 : la
    modale de saisie libre ne demande QUE le titre (voir spec Lot 1).
    """
    user = get_current_user(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    label = (body.get("label") or "").strip()
    if not label:
        raise HTTPException(422, "Titre obligatoire.")
    if len(label) > 200:
        label = label[:200]
    categorie = (body.get("categorie") or "remplacements").strip()
    if categorie not in ("controles", "entretien", "remplacements"):
        categorie = "remplacements"
    try:
        niveau = int(body.get("niveau") or 1)
    except (TypeError, ValueError):
        niveau = 1
    if niveau < 1 or niveau > 3:
        niveau = 1
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        cols = {c["name"] for c in conn.execute("PRAGMA table_info(maintenance_codes)").fetchall()}
        if "libre" not in cols:
            raise HTTPException(500, "Migration DB manquante (libre column absente).")
        # v182bis : dedup exact-match sur label. Si un code libre avec exactement
        # le meme label existe deja, on le reutilise au lieu d'en creer un nouveau.
        # Evite les LIB-xxx orphelins en cas de double-click / retry frontend.
        existing = conn.execute(
            "SELECT code, label, niveau, categorie FROM maintenance_codes "
            "WHERE libre = 1 AND label = ? LIMIT 1",
            (label,),
        ).fetchone()
        if existing:
            return {
                "code": existing["code"],
                "label": existing["label"],
                "categorie": existing["categorie"] or "remplacements",
                "niveau": int(existing["niveau"] or 1),
                "reused": True,
            }
        code = _next_libre_code(conn)
        conn.execute(
            """INSERT INTO maintenance_codes
               (code, label, niveau, categorie, periodique, intervalle,
                metrage_ref, libre, usage_count, created_at, updated_at)
               VALUES (?, ?, ?, ?, 0, '', '', 1, 0, ?, ?)""",
            (code, label, niveau, categorie, now, now),
        )
        conn.commit()
    # v182 fix : log_action attend objet=/ip= (pas target=/details=).
    try:
        log_action(
            user=user,
            action="CREATE",
            module="maintenance_libres",
            objet=f"Code libre {code} - {label}",
            ip=request.client.host if request.client else None,
        )
    except Exception:
        # L'audit ne doit jamais empecher la creation d'un code libre.
        pass
    return {"code": code, "label": label, "categorie": categorie, "niveau": niveau}


# ─── Lot 2 : Endpoints admin curation libres ─────────────────────────

@router.get("/api/maintenance/codes/libres")
def maintenance_libres_list(request: Request):
    """Liste tous les codes libres avec metadata etendue (usage_count, last_used_at).
    Pour le panneau Parametres > Maintenance > Interventions libres.
    """
    _require_maint_writer(request)
    from database import get_db
    with get_db() as conn:
        cols = {c["name"] for c in conn.execute("PRAGMA table_info(maintenance_codes)").fetchall()}
        if "libre" not in cols:
            return {"items": []}
        has_usage = "usage_count" in cols
        sel_usage = "COALESCE(c.usage_count, 0) AS usage_count" if has_usage else "0 AS usage_count"
        rows = conn.execute(
            f"""SELECT c.code, c.label, c.niveau, c.categorie,
                       {sel_usage},
                       c.created_at, c.updated_at,
                       (SELECT MAX(o.done_at) FROM maintenance_event_ops o WHERE o.code = c.code) AS last_used_at
                FROM maintenance_codes c
                WHERE c.libre = 1
                ORDER BY usage_count DESC, c.updated_at DESC"""
        ).fetchall()
    items = [{
        "code": r["code"],
        "label": r["label"],
        "niveau": int(r["niveau"] or 1),
        "categorie": r["categorie"] or "remplacements",
        "usage_count": int(r["usage_count"] or 0),
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
        "last_used_at": r["last_used_at"],
    } for r in rows]
    return {"items": items}


@router.post("/api/maintenance/codes/libres/merge")
async def maintenance_libres_merge(request: Request):
    """Fusionne deux codes libres. Body : {winner_code, loser_code}.
    Toutes les ops liees au loser sont reassignees au winner, usage_count
    est additionne, le loser est supprime. Operation reversible uniquement
    via restore SQL manuel — a annoncer explicitement cote UI."""
    user = _require_maint_writer(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    winner_code = (body.get("winner_code") or "").strip()
    loser_code = (body.get("loser_code") or "").strip()
    if not winner_code or not loser_code:
        raise HTTPException(422, "winner_code et loser_code obligatoires.")
    if winner_code == loser_code:
        raise HTTPException(400, "Les deux codes doivent etre differents.")
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        w = conn.execute(
            "SELECT libre, label, COALESCE(usage_count, 0) AS usage_count "
            "FROM maintenance_codes WHERE code = ?",
            (winner_code,),
        ).fetchone()
        l = conn.execute(
            "SELECT libre, label, COALESCE(usage_count, 0) AS usage_count "
            "FROM maintenance_codes WHERE code = ?",
            (loser_code,),
        ).fetchone()
        if not w or not l:
            raise HTTPException(404, "Un des codes est introuvable.")
        if not w["libre"] or not l["libre"]:
            raise HTTPException(400, "La fusion ne fonctionne qu'entre deux codes libres.")
        # 1. Reassigne les ops
        conn.execute(
            "UPDATE maintenance_event_ops SET code = ? WHERE code = ?",
            (winner_code, loser_code),
        )
        # 2. Additionne usage_count
        new_usage = int(w["usage_count"] or 0) + int(l["usage_count"] or 0)
        conn.execute(
            "UPDATE maintenance_codes SET usage_count = ?, updated_at = ? WHERE code = ?",
            (new_usage, now, winner_code),
        )
        # 3. Supprime le loser
        conn.execute("DELETE FROM maintenance_codes WHERE code = ?", (loser_code,))
        conn.commit()
    try:
        log_action(
            user=user, action="MERGE", module="maintenance_libres",
            objet=f"Fusion {loser_code} ({l['label']}) -> {winner_code} ({w['label']})",
            ip=request.client.host if request.client else None,
        )
    except Exception:
        pass
    return {"winner": winner_code, "loser_removed": loser_code, "new_usage_count": new_usage}


@router.patch("/api/maintenance/codes/libres/{code}")
async def maintenance_libres_rename(code: str, request: Request):
    """Renomme un code libre. Impact retroactif automatique : toutes les
    saisies passees referencant ce code refletent immediatement le nouveau
    titre (elles stockent le code, pas le label). Utilise soit depuis
    Parametres > Interventions libres, soit inline depuis l'historique."""
    user = _require_maint_writer(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    new_label = (body.get("label") or "").strip()
    if not new_label:
        raise HTTPException(422, "Titre obligatoire.")
    if len(new_label) > 200:
        new_label = new_label[:200]
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        row = conn.execute(
            "SELECT libre, label FROM maintenance_codes WHERE code = ?", (code,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Code introuvable.")
        if not row["libre"]:
            raise HTTPException(400, "Ce code n'est pas une intervention libre.")
        old_label = row["label"]
        conn.execute(
            "UPDATE maintenance_codes SET label = ?, updated_at = ? WHERE code = ?",
            (new_label, now, code),
        )
        conn.commit()
    try:
        log_action(
            user=user, action="UPDATE", module="maintenance_libres",
            objet=f"Renomme {code} : {old_label} -> {new_label}",
            ip=request.client.host if request.client else None,
        )
    except Exception:
        pass
    return {"code": code, "label": new_label}


@router.delete("/api/maintenance/codes/libres/{code}")
def maintenance_libres_delete(code: str, request: Request):
    """Supprime un code libre non utilise (usage_count = 0 ET aucune op liee).
    Sinon 409 avec message explicite invitant a fusionner."""
    user = _require_maint_writer(request)
    from database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT libre, label, COALESCE(usage_count, 0) AS usage_count "
            "FROM maintenance_codes WHERE code = ?",
            (code,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Code introuvable.")
        if not row["libre"]:
            raise HTTPException(400, "Ce code n'est pas une intervention libre.")
        real_usage = conn.execute(
            "SELECT COUNT(*) AS n FROM maintenance_event_ops WHERE code = ?", (code,)
        ).fetchone()["n"]
        eff = max(int(row["usage_count"] or 0), int(real_usage or 0))
        if eff > 0:
            raise HTTPException(
                409,
                f"Ce code a {eff} saisie(s) associee(s). Fusionne-le avec un autre titre au lieu de l'archiver.",
            )
        conn.execute("DELETE FROM maintenance_codes WHERE code = ?", (code,))
        conn.commit()
    try:
        log_action(
            user=user, action="DELETE", module="maintenance_libres",
            objet=f"Archive {code} - {row['label']}",
            ip=request.client.host if request.client else None,
        )
    except Exception:
        pass
    return {"deleted": code}


@router.get("/api/maintenance/codes/{code}/docs")
def maintenance_code_docs_list(code: str, request: Request):
    """Liste les documents attaches a un code maintenance."""
    import traceback
    try:
        get_current_user(request)
        from database import get_db
        with get_db() as conn:
            _ensure_maint_docs_table(conn)
            row = conn.execute(
                "SELECT 1 FROM maintenance_codes WHERE code=? LIMIT 1", (code,)
            ).fetchone()
            if not row:
                raise HTTPException(404, f"Code {code} introuvable.")
            rows = conn.execute(
                """SELECT id, filename, size_bytes, content_type,
                          uploaded_by, uploaded_at
                   FROM maintenance_docs
                   WHERE code=?
                   ORDER BY uploaded_at DESC, id DESC""",
                (code,),
            ).fetchall()
        return {"items": [dict(r) for r in rows]}
    except HTTPException:
        raise
    except Exception as _e:
        _tb = traceback.format_exc()
        # Remonte l'erreur telle quelle au client pour debug (temporaire).
        raise HTTPException(500, f"DEBUG: {type(_e).__name__}: {_e} | TRACE (last 400): {_tb[-400:]}")


@router.post("/api/maintenance/codes/{code}/docs")
async def maintenance_code_doc_upload(
    code: str,
    request: Request,
    file: UploadFile = File(...),
):
    """Upload d'un document rattache au code. Reservee au writer maintenance."""
    import traceback
    try:
        user = _require_maint_writer(request)
        contents = await file.read()
        if len(contents) > _MAINT_DOCS_MAX_BYTES:
            raise HTTPException(413, "Fichier trop volumineux (max 20 Mo).")
        if len(contents) == 0:
            raise HTTPException(422, "Fichier vide.")
        from database import get_db
        with get_db() as conn:
            _ensure_maint_docs_table(conn)
            row = conn.execute(
                "SELECT 1 FROM maintenance_codes WHERE code=? LIMIT 1", (code,)
            ).fetchone()
            if not row:
                raise HTTPException(404, f"Code {code} introuvable.")
        orig_name = (file.filename or "fichier").strip()
        safe = _maint_safe_filename(orig_name)
        unique = f"{uuid.uuid4().hex[:12]}_{safe}"
        dest = _maint_docs_dir(code) / unique
        with open(dest, "wb") as out:
            out.write(contents)
        rel = f"{_MAINT_DOCS_SUBDIR}/{code}/{unique}"
        now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
        author = user.get("nom") or user.get("email") or ""
        ctype = file.content_type or ""
        with get_db() as conn:
            _ensure_maint_docs_table(conn)
            cur = conn.execute(
                """INSERT INTO maintenance_docs
                   (code, filename, stored_path, size_bytes, content_type,
                    uploaded_by, uploaded_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (code, orig_name, rel, len(contents), ctype, author, now),
            )
            conn.commit()
            new_id = cur.lastrowid
        log_action(user=user, action="UPLOAD", module="maintenance_docs",
                   objet=str(new_id), detail=f"{code} · {orig_name}")
        return {"ok": True, "id": new_id, "filename": orig_name,
                "size_bytes": len(contents)}
    except HTTPException:
        raise
    except Exception as _e:
        _tb = traceback.format_exc()
        raise HTTPException(500, f"DEBUG: {type(_e).__name__}: {_e} | TRACE (last 400): {_tb[-400:]}")


@router.get("/api/maintenance/docs/{doc_id}/download")
def maintenance_doc_download(doc_id: int, request: Request):
    """Telecharge un document. Accessible a tout utilisateur connecte."""
    from fastapi.responses import FileResponse
    get_current_user(request)
    from database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT filename, stored_path FROM maintenance_docs WHERE id=?",
            (doc_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Document introuvable.")
    path_abs = Path(BASE_DIR) / row["stored_path"]
    if not path_abs.exists():
        raise HTTPException(404, "Fichier absent du disque.")
    return FileResponse(
        path=str(path_abs),
        filename=row["filename"] or path_abs.name,
    )


@router.delete("/api/maintenance/docs/{doc_id}")
def maintenance_doc_delete(doc_id: int, request: Request):
    """Suppression d'un document. Reservee au writer maintenance."""
    user = _require_maint_writer(request)
    from database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT code, filename, stored_path FROM maintenance_docs WHERE id=?",
            (doc_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Document introuvable.")
        conn.execute("DELETE FROM maintenance_docs WHERE id=?", (doc_id,))
        conn.commit()
    # Best-effort suppression fichier disque
    try:
        p = Path(BASE_DIR) / row["stored_path"]
        if p.exists():
            p.unlink()
    except Exception:
        pass
    log_action(user=user, action="DELETE", module="maintenance_docs",
               objet=str(doc_id), detail=f"{row['code']} · {row['filename']}")
    return {"ok": True}



# ── Alertes de maintenance ─────────────────────────────────────────
# Modèle data-driven : chaque alerte stocke ses paramètres (déclencheur, cible,
# formulaire de validation, comportement bloquant, etc.) dans `params` au format
# JSON. Le code n'a pas besoin de connaître la structure exacte — elle évolue
# librement à mesure que les types de règles s'enrichissent. Seul le super
# admin peut créer / modifier / supprimer / activer une alerte. Toute alerte
# est inactive à la création (active=0) : l'admin doit l'activer explicitement.

import json as _json_alerts


def _check_blocking_alert_due(conn, user, machine: str) -> bool:
    """v2.2.88 — Retourne True si au moins une alerte bloquante (block_production=True)
    est actuellement due pour cette machine. Utilisé par /api/fabrication/saisie
    comme garde-fou pour refuser une saisie tant qu'une alerte non-ack existe.

    Réutilise la même logique de détection que /api/maintenance/alerts/active
    en la simplifiant : on veut juste savoir s'il existe UNE alerte due bloquante.
    """
    if not machine:
        return False
    try:
        rows = conn.execute(
            "SELECT id, params FROM maintenance_alerts WHERE active=1"
        ).fetchall()
    except Exception:
        return False
    now_paris = datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    # Pas de gap : le garde-fou doit être strict, pas soumis à min_gap.
    user_role = user.get("role") if user else ""
    user_machine = machine
    for r in rows:
        try:
            params = _json_alerts.loads(r["params"] or "{}")
        except (ValueError, TypeError):
            continue
        # Ne considère que les alertes bloquantes
        if not bool(params.get("block_production", False)):
            continue
        target = params.get("target") or {}
        if not operator_should_see_alert(user_role, user_machine, target):
            # Superadmin voit tout ; sinon on skippe si machine hors cible
            if user_role != ROLE_SUPERADMIN:
                continue
        trig = params.get("trigger") or {}
        ttype = trig.get("type")
        if ttype == "periodic":
            try:
                if _is_periodic_alert_due(conn, int(r["id"]), params, machine, now_paris):
                    return True
            except Exception:
                continue
        elif ttype == "event":
            event = str(trig.get("event") or "").strip()
            if event == "after_calage":
                # Réutilise la logique after_calage : dernière saisie machine = calage
                _calage_window = (now_paris - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%S")
                _window = (now_paris - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
                _last_row = conn.execute(
                    """SELECT no_dossier, operation_category, date_operation
                       FROM production_data
                       WHERE machine=? AND date_operation >= ?
                       ORDER BY date_operation DESC LIMIT 1""",
                    (machine, _window),
                ).fetchone()
                if not _last_row:
                    continue
                if (_last_row["operation_category"] or "").lower() != "calage":
                    continue
                if not _last_row["no_dossier"] or not str(_last_row["no_dossier"]).strip():
                    continue
                if _last_row["date_operation"] < _calage_window:
                    continue
                _dos = str(_last_row["no_dossier"]).strip()
                _ack_check = conn.execute(
                    """SELECT 1 FROM maintenance_alert_acks
                       WHERE alert_id=? AND no_dossier=? LIMIT 1""",
                    (int(r["id"]), _dos),
                ).fetchone()
                if _ack_check:
                    continue
                _last_89 = conn.execute(
                    """SELECT MAX(date_operation) AS m FROM production_data
                       WHERE no_dossier=? AND machine=? AND operation_code='89'""",
                    (_dos, machine),
                ).fetchone()
                _last_89_at = _last_89["m"] if _last_89 else None
                if _last_89_at and _last_row["date_operation"] <= _last_89_at:
                    continue
                return True
            # Autres events (dossier_start / dossier_end) : pas implémentés
            # comme bloquants pour l'instant. Reste ouvert pour extension.
    return False


def _require_alerts_admin(request: Request) -> dict:
    """v2.2.18 — Élargi aux rôles direction et administration pour permettre
    la gestion des alertes maintenance depuis MyMaintenance (l'admin métier
    n'a pas accès à /settings mais peut gérer les alertes depuis sa vue).
    v2.2.74 — Élargi aux nouveaux rôles administration_ventes et
    administration_technique (cohérence avec l'accès à MyMaintenance côté
    admin, gate déjà ouverte dans maintenance_events._ADMIN_ROLES v2.2.46).
    """
    user = get_current_user(request)
    if user.get("role") not in (
        ROLE_SUPERADMIN,
        ROLE_DIRECTION,
        ROLE_ADMINISTRATION,
        ROLE_ADMINISTRATION_VENTES,
        ROLE_ADMINISTRATION_TECHNIQUE,
    ):
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs maintenance.")
    return user


def _alert_row_to_dict(r) -> dict:
    try:
        params = _json_alerts.loads(r["params"] or "{}")
    except (ValueError, TypeError):
        params = {}
    # linked_maint_code / last_ack_at : peuvent être absents sur les vieilles DB
    # (avant migration v133).
    try:
        linked = r["linked_maint_code"]
    except (IndexError, KeyError):
        linked = None
    try:
        last_ack = r["last_ack_at"]
    except (IndexError, KeyError):
        last_ack = None
    raw_creator = r["created_by"] or ""
    try:
        creator_nom = r["creator_nom"]
    except (IndexError, KeyError):
        creator_nom = None
    # created_by_display : nom lisible pour l'UI, vide pour les valeurs
    # synthétiques (auto:migration, auto:code-sync)
    if not raw_creator or raw_creator.startswith("auto:"):
        created_by_display = ""
    elif creator_nom:
        created_by_display = creator_nom
    else:
        created_by_display = raw_creator
    return {
        "id": int(r["id"]),
        "nom": r["nom"],
        "active": bool(r["active"]),
        "params": params,
        "created_by": raw_creator,
        "created_by_display": created_by_display,
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
        "linked_maint_code": linked or "",
        "last_ack_at": last_ack or "",
    }


@router.get("/api/maintenance/alerts")
def maintenance_alerts_list(request: Request):
    """Lecture des alertes : super admin uniquement (les opérateurs ne voient pas
    cette liste — ils ne voient que les alertes actives au moment du déclenchement)."""
    _require_alerts_admin(request)
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT a.id, a.nom, a.active, a.params, a.created_by,
                      a.created_at, a.updated_at,
                      a.linked_maint_code, a.last_ack_at,
                      u.nom AS creator_nom
               FROM maintenance_alerts a
               LEFT JOIN users u ON u.email = a.created_by
               ORDER BY (a.linked_maint_code IS NULL), a.linked_maint_code, a.created_at DESC, a.id DESC"""
        ).fetchall()
    return {"items": [_alert_row_to_dict(r) for r in rows]}


@router.post("/api/maintenance/alerts")
async def maintenance_alerts_create(request: Request):
    """Création d'une alerte. Toujours inactive à la naissance (active=0).
    Les paramètres détaillés (déclencheur, cible, formulaire) sont stockés en
    JSON dans `params` — l'UI les enrichit ensuite via PATCH."""
    user = _require_alerts_admin(request)
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(422, "Nom obligatoire.")
    if len(nom) > 120:
        nom = nom[:120]
    params_raw = body.get("params") or {}
    params_validated = _validate_alert_params(params_raw)
    try:
        params_json = _json_alerts.dumps(params_validated, ensure_ascii=False)
    except (TypeError, ValueError):
        raise HTTPException(422, "params non sérialisable en JSON.")
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO maintenance_alerts
               (nom, active, params, created_by, created_at, updated_at)
               VALUES (?, 0, ?, ?, ?, ?)""",
            (nom, params_json, user.get("email") or user.get("nom") or "", now, now),
        )
        new_id = cur.lastrowid
        conn.commit()
    log_action(user=user, action="CREATE", module="maintenance_alerts",
               objet=str(new_id), detail=nom)
    return {"ok": True, "id": new_id}


@router.patch("/api/maintenance/alerts/{alert_id}")
async def maintenance_alerts_update(alert_id: int, request: Request):
    """Mise à jour partielle : nom, params, active. Le toggle d'activation
    passe par ici (body = {"active": true/false})."""
    user = _require_alerts_admin(request)
    body = await request.json()
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    sets = []
    vals = []
    action_detail_parts = []
    if "nom" in body:
        # Bloquer le rename d'une alerte auto : le nom doit rester synchronisé
        # avec le code source. La personnalisation passe par les params.
        from database import get_db as _gd_check
        with _gd_check() as _cn:
            _row = _cn.execute(
                "SELECT linked_maint_code FROM maintenance_alerts WHERE id=?",
                (alert_id,),
            ).fetchone()
        _linked = None
        if _row is not None:
            try:
                _linked = _row["linked_maint_code"]
            except (IndexError, KeyError):
                _linked = None
        if _linked:
            raise HTTPException(
                409,
                "Le nom d'une alerte auto-générée est synchronisé avec son code "
                "maintenance — modifier le code (ou son libellé) à la place.",
            )
        nom = (body.get("nom") or "").strip()
        if not nom:
            raise HTTPException(422, "Nom obligatoire.")
        if len(nom) > 120:
            nom = nom[:120]
        sets.append("nom=?")
        vals.append(nom)
        action_detail_parts.append(f"nom={nom!r}")
    if "params" in body:
        params_raw = body.get("params") or {}
        params_validated = _validate_alert_params(params_raw)
        try:
            params_json = _json_alerts.dumps(params_validated, ensure_ascii=False)
        except (TypeError, ValueError):
            raise HTTPException(422, "params non sérialisable en JSON.")
        sets.append("params=?")
        vals.append(params_json)
        action_detail_parts.append("params updated")
    if "active" in body:
        active = 1 if body.get("active") else 0
        sets.append("active=?")
        vals.append(active)
        action_detail_parts.append(f"active={bool(active)}")
    if not sets:
        raise HTTPException(422, "Aucun champ à mettre à jour.")
    sets.append("updated_at=?")
    vals.append(now)
    vals.append(alert_id)
    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE maintenance_alerts SET {', '.join(sets)} WHERE id=?",
            tuple(vals),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Alerte introuvable.")
    log_action(user=user, action="UPDATE", module="maintenance_alerts",
               objet=str(alert_id), detail=" ; ".join(action_detail_parts))
    return {"ok": True, "id": alert_id}


@router.delete("/api/maintenance/alerts/{alert_id}")
def maintenance_alerts_delete(alert_id: int, request: Request):
    user = _require_alerts_admin(request)
    from database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT linked_maint_code FROM maintenance_alerts WHERE id=?",
            (alert_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Alerte introuvable.")
        linked = None
        try:
            linked = row["linked_maint_code"]
        except (IndexError, KeyError):
            linked = None
        if linked:
            raise HTTPException(
                409,
                "Alerte auto-générée — la suppression passe par la suppression du "
                "code maintenance associé (ou par son passage en périodique / "
                "interventions).",
            )
        cur = conn.execute("DELETE FROM maintenance_alerts WHERE id=?", (alert_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Alerte introuvable.")
    log_action(user=user, action="DELETE", module="maintenance_alerts",
               objet=str(alert_id), detail="")
    return {"ok": True}


@router.post("/api/maintenance/alerts/disable-all")
def maintenance_alerts_disable_all(request: Request):
    """Kill switch : désactive toutes les alertes en un appel. Sécurité au cas
    où une alerte mal configurée bloque l'atelier — ne supprime rien, juste
    bascule active=0 partout."""
    user = _require_alerts_admin(request)
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE maintenance_alerts SET active=0, updated_at=? WHERE active=1",
            (now,),
        )
        affected = cur.rowcount
        conn.commit()
    log_action(user=user, action="UPDATE", module="maintenance_alerts",
               objet="ALL", detail=f"disable-all : {affected} désactivée(s)")
    return {"ok": True, "disabled": affected}


@router.get("/api/maintenance/alert-settings")
def maintenance_alert_settings_get(request: Request):
    """Réglages globaux des alertes (singleton)."""
    _require_alerts_admin(request)
    from database import get_db
    with get_db() as conn:
        # v2.2.23 : ajoute min_gap_minutes au SELECT (bug historique : la valeur
        # était toujours renvoyée à 5 car la colonne n'était pas sélectionnée).
        r = conn.execute(
            "SELECT placement, size, block_production, stack_mode, "
            "min_gap_minutes, updated_at, updated_by "
            "FROM maintenance_alert_settings WHERE id=1"
        ).fetchone()
    if not r:
        return {
            "placement": "top-right",
            "size": "medium",
            "block_production": False,
            "stack_mode": "queue",
            "min_gap_minutes": 5,
            "updated_at": None,
            "updated_by": "",
        }
    try:
        stack_mode = r["stack_mode"]
    except (IndexError, KeyError):
        stack_mode = "queue"
    try:
        min_gap = r["min_gap_minutes"]
    except (IndexError, KeyError):
        min_gap = 5
    placement = r["placement"] or "center"
    if placement not in _ALERT_PLACEMENTS:
        placement = "center"
    try:
        min_gap_val = int(min_gap) if min_gap is not None else 5
    except (TypeError, ValueError):
        min_gap_val = 5
    if min_gap_val < 0:
        min_gap_val = 0
    return {
        "placement": placement,
        "size": r["size"] or "medium",
        "block_production": bool(r["block_production"]),
        "stack_mode": stack_mode or "queue",
        "min_gap_minutes": min_gap_val,
        "updated_at": r["updated_at"],
        "updated_by": r["updated_by"] or "",
    }


@router.put("/api/maintenance/alert-settings")
async def maintenance_alert_settings_update(request: Request):
    user = _require_alerts_admin(request)
    body = await request.json()
    placement = (body.get("placement") or "center").strip()
    size = (body.get("size") or "medium").strip()
    block_production = 1 if body.get("block_production") else 0
    # stack_mode : forcé à 'queue' (le seul mode UI désormais). On ignore la
    # valeur reçue plutôt que de renvoyer 422 pour rester tolérant.
    stack_mode = "queue"
    # min_gap_minutes : délai de silence après chaque ack. 0 = pas de gap.
    try:
        min_gap_val = int(body.get("min_gap_minutes")) if body.get("min_gap_minutes") is not None else 5
    except (TypeError, ValueError):
        min_gap_val = 5
    if min_gap_val < 0:
        min_gap_val = 0
    if min_gap_val > 120:
        min_gap_val = 120
    if placement not in _ALERT_PLACEMENTS:
        raise HTTPException(422, f"placement invalide : {placement!r}.")
    if size not in _ALERT_SIZES:
        raise HTTPException(422, f"size invalide : {size!r}.")
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    who = user.get("email") or user.get("nom") or ""
    with get_db() as conn:
        # Détection défensive des colonnes : si v135 n'a pas encore été appliquée
        # sur cette DB (mise à jour partielle, pull sans restart, etc.), on tombe
        # gracieusement sur le schéma v134 sans stack_mode plutôt que de planter
        # avec un 500.
        cols = {r["name"] for r in conn.execute(
            "PRAGMA table_info(maintenance_alert_settings)"
        ).fetchall()}
        has_stack_mode = "stack_mode" in cols
        # Détecte aussi la présence de min_gap_minutes (v138)
        has_min_gap = "min_gap_minutes" in cols
        if has_stack_mode and has_min_gap:
            conn.execute(
                """INSERT INTO maintenance_alert_settings
                   (id, placement, size, block_production, stack_mode,
                    min_gap_minutes, updated_at, updated_by)
                   VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     placement=excluded.placement,
                     size=excluded.size,
                     block_production=excluded.block_production,
                     stack_mode=excluded.stack_mode,
                     min_gap_minutes=excluded.min_gap_minutes,
                     updated_at=excluded.updated_at,
                     updated_by=excluded.updated_by""",
                (placement, size, block_production, stack_mode, min_gap_val, now, who),
            )
        elif has_stack_mode:
            conn.execute(
                """INSERT INTO maintenance_alert_settings
                   (id, placement, size, block_production, stack_mode,
                    updated_at, updated_by)
                   VALUES (1, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     placement=excluded.placement,
                     size=excluded.size,
                     block_production=excluded.block_production,
                     stack_mode=excluded.stack_mode,
                     updated_at=excluded.updated_at,
                     updated_by=excluded.updated_by""",
                (placement, size, block_production, stack_mode, now, who),
            )
        else:
            # Fallback v134 — stack_mode silencieusement ignoré.
            conn.execute(
                """INSERT INTO maintenance_alert_settings
                   (id, placement, size, block_production,
                    updated_at, updated_by)
                   VALUES (1, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     placement=excluded.placement,
                     size=excluded.size,
                     block_production=excluded.block_production,
                     updated_at=excluded.updated_at,
                     updated_by=excluded.updated_by""",
                (placement, size, block_production, now, who),
            )
        conn.commit()
    log_action(user=user, action="UPDATE", module="maintenance_alerts",
               objet="settings",
               detail=f"placement={placement} size={size} "
                      f"block={bool(block_production)} stack={stack_mode} "
                      f"gap={min_gap_val}min")
    return {"ok": True}


# ── Affichage opérateur : alertes actives et acquittements ─────────
# L'endpoint /active est polled par /prod toutes les ~15 secondes. Il calcule
# pour chaque alerte active si elle doit s'afficher MAINTENANT pour cet
# opérateur, sur sa machine, selon la sémantique de déclenchement.
#
# Pour le périodique :
#   - Référence = MAX(dernier_ack, dernière_saisie_01_ou_88 sur la machine)
#   - Si la machine n'est plus en production (dernière saisie = 89 ou arrêt
#     50-85), on n'affiche pas
#   - Si la dernière "remise en marche" est un code 88, un délai de grâce de
#     ALERT_RESUME_GRACE_MINUTES (5 min) est appliqué après ce 88 — l'alerte
#     ne se déclenche pas avant reprise + 5 min
#
# Pour les autres types (manual / calendar / event) : non implémentés en v1,
# silencieusement ignorés.


def _parse_paris_dt(s):
    """Parse une date stockée au format MySifa (Paris local, sans tz)."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s)[:19])
    except (ValueError, TypeError):
        return None


def _machine_name_from_user(conn, user: dict) -> Optional[str]:
    """Récupère le nom de la machine sur laquelle l'opérateur travaille.

    Stratégie :
      1. machine_id explicitement assignée au compte (cas standard)
      2. Fallback : machine de la dernière saisie du jour pour cet opérateur
         — utile pour les comptes flexibles (admin qui teste, opérateur
         non rattaché en permanence à une machine, etc.)
    """
    # 1. machine_id du compte
    mid = user.get("machine_id")
    if mid:
        try:
            row = conn.execute("SELECT nom FROM machines WHERE id=? LIMIT 1", (int(mid),)).fetchone()
        except (TypeError, ValueError):
            row = None
        if row and row["nom"]:
            return row["nom"]
    # 2. Fallback : dernière saisie du jour de cet opérateur
    user_label = user.get("nom") or user.get("email") or ""
    if not user_label:
        return None
    today_paris = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT machine FROM production_data "
        "WHERE operateur=? AND date_operation LIKE ? "
        "ORDER BY date_operation DESC, id DESC LIMIT 1",
        (user_label, today_paris + "%"),
    ).fetchone()
    if row and row["machine"]:
        return row["machine"]
    return None


def _is_machine_in_production(conn, machine: str) -> bool:
    """True si la dernière saisie pour cette machine est code 01, 03 ou 88."""
    row = conn.execute(
        "SELECT operation_code FROM production_data "
        "WHERE machine=? ORDER BY date_operation DESC, id DESC LIMIT 1",
        (machine,)
    ).fetchone()
    if not row:
        return False
    code = str(row["operation_code"] or "").strip()
    # v2.2.83 : 01 (Début prod) ne compte plus comme "en production"
    return code in ("03", "88")


def _is_periodic_alert_due(conn, alert_id: int, params: dict, machine: str, now_paris: datetime) -> bool:
    """Décide si une alerte périodique doit s'afficher maintenant pour cette machine.

    Logique :
      1. Trouver le dernier code d'arrêt pour cette machine (87, 89, ou 50-85)
      2. Déterminer le DÉBUT de la session de production en cours :
         - Si arrêt récent → premier événement 01/03/88 APRÈS cet arrêt (= reprise)
         - Sinon → premier événement 01/03/88 jamais (= début initial)
      3. Ancre = max(session_start, last_ack pour cette alerte+machine)
      4. due = ancre + intervalle
      5. Grâce : si on est dans une session démarrée par une reprise (donc
         session_start > last_stop) ET aucun ack postérieur à session_start,
         alors due = max(due, session_start + 5 min)
    """
    trig = params.get("trigger") or {}
    if trig.get("type") != "periodic":
        return False
    try:
        interval_min = int(trig.get("interval_minutes") or 0)
    except (TypeError, ValueError):
        interval_min = 0
    if interval_min <= 0:
        return False
    if not _is_machine_in_production(conn, machine):
        return False

    # 1. Dernier événement "non-production" pour cette machine.
    # Définition symétrique de _is_machine_in_production : tout code qui n'est
    # PAS dans {01, 03, 88} interrompt la session. Ça couvre les arrêts
    # explicites (89, 87, 50-85) mais AUSSI le Calage (02), les événements
    # personnel (86), les annulations (90), etc. Toute interruption remet le
    # compteur à zéro et déclenche la grâce de 5 min à la reprise.
    # v2.2.83 : 01 (Début prod) devient un code "stop" (interrompt la session)
    last_stop_row = conn.execute(
        """SELECT MAX(date_operation) AS m FROM production_data
           WHERE machine=? AND operation_code NOT IN ('03', '88')
           AND operation_code IS NOT NULL AND operation_code != ''""",
        (machine,),
    ).fetchone()
    last_stop_iso = last_stop_row["m"] if last_stop_row else None
    last_stop_dt = _parse_paris_dt(last_stop_iso)

    # 2. Début de la session courante : premier 01/03/88 après last_stop
    if last_stop_iso:
        session_row = conn.execute(
            """SELECT MIN(date_operation) AS m FROM production_data
               WHERE machine=? AND operation_code IN ('03', '88')
               AND date_operation > ?""",
            (machine, last_stop_iso),
        ).fetchone()
    else:
        session_row = conn.execute(
            """SELECT MIN(date_operation) AS m FROM production_data
               WHERE machine=? AND operation_code IN ('03', '88')""",
            (machine,),
        ).fetchone()
    session_start_dt = _parse_paris_dt(session_row["m"]) if session_row else None
    if not session_start_dt:
        return False

    # 3. Dernier ack pour cette alerte sur cette machine
    ack_row = conn.execute(
        "SELECT MAX(ack_at) AS m FROM maintenance_alert_acks "
        "WHERE alert_id=? AND machine=?",
        (alert_id, machine),
    ).fetchone()
    last_ack_dt = _parse_paris_dt(ack_row["m"]) if ack_row else None

    # Deux cas :
    #  - AUCUN ack dans la session courante → première alerte de session,
    #    due = session_start + délai de grâce (5 min). Uniforme quel que soit
    #    l'intervalle configuré : la grâce sert de "ramp-up" à la reprise.
    #  - Ack déjà validé dans la session → rythme normal, due = ack + intervalle.
    has_ack_in_session = (
        last_ack_dt is not None and last_ack_dt >= session_start_dt
    )
    if has_ack_in_session:
        due_dt = last_ack_dt + timedelta(minutes=interval_min)
    else:
        # Grâce personnalisable par alerte, fallback sur la constante globale
        try:
            grace_min = int(trig.get("grace_minutes", ALERT_RESUME_GRACE_MINUTES))
        except (TypeError, ValueError):
            grace_min = ALERT_RESUME_GRACE_MINUTES
        if grace_min < 0:
            grace_min = 0
        due_dt = session_start_dt + timedelta(minutes=grace_min)

    return now_paris >= due_dt


@router.get("/api/maintenance/alerts/active")
def maintenance_alerts_active(request: Request):
    """Liste des alertes actives à pousser sur l'écran de l'opérateur connecté.
    Filtre par rôle (superadmin voit tout, fabrication voit les siennes), par
    machine ciblée, et applique la sémantique de déclenchement (périodique).
    """
    from database import get_db
    user = get_current_user(request)
    user_role = user.get("role") or ""
    operateur = (user.get("operateur_lie") or user.get("nom") or "").strip()
    user_nom = (user.get("nom") or "").strip()
    now_paris = datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    items = []
    gap_until_str = None
    gap_active = False
    with get_db() as conn:
        user_machine = _machine_name_from_user(conn, user)
        # Gap : calcule si un ack recent existe sur cette machine. Ne bloque
        # QUE les alertes periodiques -- les alertes evenementielles bypassent
        # ce silence, car elles sont declenchees par l'action metier de
        # l'operateur (fin/debut de dossier). Sinon un operateur qui clot un
        # dossier juste apres un ack ne verrait jamais l'alerte suivante.
        if user_machine:
            settings_row = conn.execute(
                "SELECT min_gap_minutes FROM maintenance_alert_settings WHERE id=1"
            ).fetchone()
            try:
                min_gap_min = int(settings_row["min_gap_minutes"]) if settings_row else 5
            except (TypeError, ValueError, KeyError, IndexError):
                min_gap_min = 5
            if min_gap_min > 0:
                gap_row = conn.execute(
                    "SELECT MAX(ack_at) AS m FROM maintenance_alert_acks "
                    "WHERE machine=?",
                    (user_machine,),
                ).fetchone()
                last_any_ack_dt = _parse_paris_dt(gap_row["m"]) if gap_row else None
                if last_any_ack_dt is not None:
                    gap_end = last_any_ack_dt + timedelta(minutes=min_gap_min)
                    if now_paris < gap_end:
                        gap_active = True
                        gap_until_str = gap_end.strftime("%Y-%m-%dT%H:%M:%S")
        rows = conn.execute(
            """SELECT id, nom, params, linked_maint_code
               FROM maintenance_alerts
               WHERE active=1"""
        ).fetchall()
        for r in rows:
            try:
                params = _json_alerts.loads(r["params"] or "{}")
            except (ValueError, TypeError):
                params = {}
            target = params.get("target") or {}
            # Filtrage cible : superadmin voit tout ; sinon fabrication uniquement
            if not operator_should_see_alert(user_role, user_machine or "", target):
                continue
            trig = params.get("trigger") or {}
            ttype = trig.get("type")
            should_show = False
            # v163+ : no_dossier du dossier qui a déclenché l'alerte (pour les
            # events dossier_start/dossier_end). Sera renvoyé au client pour
            # qu'il l'utilise à l'ack, garantissant la cohérence de l'historique.
            trigger_no_dossier = ""
            if ttype == "periodic":
                if gap_active:
                    continue
                machine_for_check = user_machine
                # Si superadmin sans machine assignée et la cible est une seule
                # machine spécifique, on utilise cette machine pour le calcul.
                if not machine_for_check and user_role == ROLE_SUPERADMIN:
                    machines_list = target.get("machines") or []
                    if isinstance(machines_list, list):
                        specific = [m for m in machines_list if m and m != "*"]
                        if len(specific) == 1:
                            machine_for_check = specific[0]
                if machine_for_check:
                    should_show = _is_periodic_alert_due(
                        conn, int(r["id"]), params, machine_for_check, now_paris
                    )
            elif ttype == "event":
                # Trigger evenementiel : l'alerte s'affiche quand un evenement
                # metier correspondant s'est produit APRES le dernier ack de
                # cette alerte sur cette machine. Bypass du gap : l'alerte
                # suit strictement les actions saisies sur la MACHINE (pas sur
                # l'user connecté — le super admin, le responsable et l'opérateur
                # de nuit peuvent tous ouvrir /maintenance et l'alerte doit
                # se comporter identiquement).
                # Evenements supportes :
                #   dossier_end   -> saisie operation_code = '89' (fin prod)
                #   dossier_start -> saisie operation_code = '01' (debut prod)
                event = str(trig.get("event") or "").strip()
                op_code = None
                if event == "dossier_end":
                    op_code = "89"
                elif event == "dossier_start":
                    op_code = "01"
                elif event == "after_calage":
                    # v2.2.76 : traité en bloc plus bas — nécessite une logique
                    # spécifique (parcours de la séquence des saisies du dossier).
                    pass
                # v164 : fallback super admin (comme la branche periodic).
                # Si Loic (superadmin) ouvre /prod ou /maintenance sans machine
                # assignée dans son profil, on utilise la machine cible de
                # l'alerte si elle est unique. Sans ça, un super admin ne verrait
                # JAMAIS les alertes événementielles, ce qui empêche tout test.
                effective_machine = user_machine
                if not effective_machine and user_role == ROLE_SUPERADMIN:
                    machines_list = target.get("machines") or []
                    if isinstance(machines_list, list):
                        specific = [m for m in machines_list if m and m != "*"]
                        if len(specific) == 1:
                            effective_machine = specific[0]
                effective_operateur = operateur or (user_nom if user_role == ROLE_SUPERADMIN else "")
                # v2.2.88 : cas after_calage — nouvelle logique. L'alerte doit
                # s'afficher AVANT la saisie de production, donc quand la dernière
                # saisie machine est un code CALAGE (pas un prod). Verrou dossier
                # via ack. Contraintes conservées : fenêtre 4h, post-89.
                if event == "after_calage" and effective_machine:
                    _window = (now_paris - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
                    _calage_window = (now_paris - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%S")
                    _last_row = conn.execute(
                        """SELECT no_dossier, operation_code, operation_category, date_operation
                           FROM production_data
                           WHERE machine=? AND date_operation >= ?
                           ORDER BY date_operation DESC LIMIT 1""",
                        (effective_machine, _window),
                    ).fetchone()
                    # Nouvelle contrainte : dernière saisie = catégorie calage
                    # avec no_dossier renseigné et dans la fenêtre 4h.
                    _is_calage_last = (
                        _last_row
                        and (_last_row["operation_category"] or "").lower() == "calage"
                        and _last_row["no_dossier"] is not None
                        and str(_last_row["no_dossier"]).strip() != ""
                        and _last_row["date_operation"] >= _calage_window
                    )
                    if _is_calage_last:
                        _dos = str(_last_row["no_dossier"]).strip()
                        _last_calage_at = _last_row["date_operation"]
                        # Verrou par dossier
                        _ack_check = conn.execute(
                            """SELECT 1 FROM maintenance_alert_acks
                               WHERE alert_id=? AND no_dossier=? LIMIT 1""",
                            (int(r["id"]), _dos),
                        ).fetchone()
                        if not _ack_check:
                            # Contrainte v2.2.82 conservée : calage doit être
                            # postérieur au dernier code 89 du dossier.
                            _last_89 = conn.execute(
                                """SELECT MAX(date_operation) AS m FROM production_data
                                   WHERE no_dossier=? AND machine=? AND operation_code='89'""",
                                (_dos, effective_machine),
                            ).fetchone()
                            _last_89_at = _last_89["m"] if _last_89 else None
                            if not _last_89_at or _last_calage_at > _last_89_at:
                                should_show = True
                                trigger_no_dossier = _dos
                elif op_code and effective_machine and effective_operateur:
                    last_ack = conn.execute(
                        "SELECT MAX(ack_at) AS m FROM maintenance_alert_acks "
                        "WHERE alert_id=? AND machine=?",
                        (int(r["id"]), user_machine),
                    ).fetchone()
                    last_ack_at_str = last_ack["m"] if last_ack else None
                    # Filtre par opérateur : seul celui qui a saisi le 89 (ou son
                    # équivalent user_nom) voit l'alerte. Évite les faux positifs
                    # "un autre op a fait le 89 → alerte chez tout le monde".
                    q = ("SELECT no_dossier FROM production_data "
                         "WHERE machine=? AND operation_code=? "
                         "  AND (operateur=? OR operateur=?)")
                    p = [user_machine, op_code, operateur, user_nom or operateur]
                    if last_ack_at_str:
                        q += " AND date_operation > ?"
                        p.append(last_ack_at_str)
                    else:
                        q += " AND date_operation >= ?"
                        p.append(now_paris.strftime("%Y-%m-%dT00:00:00"))
                    q += " ORDER BY date_operation DESC LIMIT 1"
                    recent = conn.execute(q, tuple(p)).fetchone()
                    should_show = recent is not None
                    if recent and recent["no_dossier"]:
                        trigger_no_dossier = str(recent["no_dossier"]).strip()
                    # Filtre par conditionnement (bobine / plis) — v163+
                    # Options : 'any' (défaut), 'bobine_only', 'plis_only'.
                    # Critères STRICTS bobine : mandrin_dia renseigné, OU
                    # mandrin_longueur > 0, OU mot "bobine" dans le texte du
                    # conditionnement. nb_etiq_bobin / nb_bobines_carton NE
                    # comptent PLUS (trop de faux positifs sur templates).
                    # Politique : si la fiche a des infos conditionnement mais
                    # aucun indicateur bobine → alerte silencieuse (c'est du plis).
                    # Si la fiche est vide (aucun signal) → alerte fire quand même
                    # (mieux vaut alerter et laisser décider que rater).
                    if should_show:
                        filter_cond = str(trig.get("filter_conditionnement") or "any").strip()
                        if filter_cond in ("bobine_only", "plis_only"):
                            no_dossier = recent["no_dossier"] if recent else None
                            is_bobine = None  # None = inconnu, on ne filtre pas
                            if no_dossier:
                                cond_row = conn.execute(
                                    """SELECT ft.conditionnement_norm, ft.conditionnement,
                                              ft.mandrin_dia, ft.mandrin_longueur
                                       FROM planning_entries pe
                                       LEFT JOIN fiches_techniques ft
                                              ON ft.ref_produit_norm = pe.ref_produit_norm
                                       WHERE pe.reference = ?
                                       ORDER BY pe.id DESC LIMIT 1""",
                                    (no_dossier,),
                                ).fetchone()
                                if cond_row:
                                    cn = (cond_row["conditionnement_norm"] or "").lower()
                                    cr = (cond_row["conditionnement"] or "").lower()
                                    mandrin_dia = (cond_row["mandrin_dia"] or "").strip()
                                    try:
                                        mandrin_long = float(cond_row["mandrin_longueur"] or 0)
                                    except (TypeError, ValueError):
                                        mandrin_long = 0.0
                                    has_mandrin = bool(mandrin_dia) or (mandrin_long > 0)
                                    has_text_bobine = ("bobine" in cn) or ("bobine" in cr)
                                    # A-t-on la moindre info de conditionnement ?
                                    has_any_cond_info = bool(
                                        mandrin_dia or mandrin_long > 0 or cn or cr
                                    )
                                    if has_any_cond_info:
                                        # Info dispo → décision ferme
                                        is_bobine = has_mandrin or has_text_bobine
                                    # Sinon is_bobine reste None (inconnu → fire)
                            # Applique le filtre uniquement si is_bobine est déterminé
                            if is_bobine is True and filter_cond == "plis_only":
                                should_show = False
                            elif is_bobine is False and filter_cond == "bobine_only":
                                should_show = False
                            elif filter_cond == "plis_only" and is_bobine:
                                should_show = False
            # type manual / calendar : non implémenté en v1
            if should_show:
                # v163+ : fallback no_dossier pour toutes les alertes qui n'ont
                # pas encore de trigger_no_dossier (typiquement les périodiques).
                # On prend le dernier no_dossier touché aujourd'hui sur la MACHINE
                # (peu importe qui a saisi et peu importe 01/89). Sémantique
                # « atelier » : le dossier courant est celui qui tourne sur la
                # machine, pas celui du user connecté (qui peut être super admin,
                # responsable, opérateur en pause, etc.). Couvre :
                #   - dossier en cours (01 sans 89)
                #   - dossier juste terminé (89 récent)
                #   - transition 89 -> 01 du suivant
                if not trigger_no_dossier and user_machine:
                    last_touched = conn.execute(
                        """SELECT no_dossier FROM production_data
                           WHERE machine=?
                             AND date_operation >= ?
                             AND no_dossier IS NOT NULL AND TRIM(no_dossier) != ''
                           ORDER BY date_operation DESC LIMIT 1""",
                        (user_machine, now_paris.strftime("%Y-%m-%dT00:00:00")),
                    ).fetchone()
                    if last_touched and last_touched["no_dossier"]:
                        trigger_no_dossier = str(last_touched["no_dossier"]).strip()
                items.append({
                    "id": int(r["id"]),
                    "nom": r["nom"],
                    "params": params,
                    "linked_maint_code": r["linked_maint_code"] or "",
                    # no_dossier du dossier qui a déclenché l'alerte (peut être
                    # vide pour les alertes non-événementielles ou si l'event
                    # métier ne référence pas de dossier).
                    "no_dossier": trigger_no_dossier,
                })
    resp = {"items": items, "now": now_paris.strftime("%Y-%m-%dT%H:%M:%S")}
    if gap_until_str:
        resp["gap_until"] = gap_until_str
    return resp


@router.get("/api/maintenance/alert-acks")
def maintenance_alert_acks_list(request: Request):
    """Historique des acquittements d'alertes maintenance pour l'app /maintenance.
    Accessible aux administrateurs (superadmin, direction, administration) et
    aux opérateurs autorisés à voir la page Maintenance."""
    user = get_current_user(request)
    # Mêmes droits d'accès que l'app /maintenance : tout utilisateur authentifié
    # peut lire (filtrage UI côté maintenance_page selon ses propres règles).
    date_from = request.query_params.get("from")
    date_to = request.query_params.get("to")
    machine_filter = request.query_params.get("machine") or ""
    where = []
    params_sql = []
    if date_from:
        where.append("a.ack_at >= ?")
        params_sql.append(str(date_from) + "T00:00:00")
    if date_to:
        where.append("a.ack_at <= ?")
        params_sql.append(str(date_to) + "T23:59:59")
    if machine_filter:
        where.append("a.machine = ?")
        params_sql.append(machine_filter)
    where.append("a.dismissed = 0")
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT a.id, a.alert_id, al.nom AS alert_nom,
                       al.linked_maint_code, a.user_id, a.user_nom,
                       a.machine, a.no_dossier, a.ack_at,
                       a.responses, a.comment
                FROM maintenance_alert_acks a
                LEFT JOIN maintenance_alerts al ON al.id = a.alert_id
                {where_sql}
                ORDER BY a.ack_at DESC
                LIMIT 1000""",
            tuple(params_sql),
        ).fetchall()
    items = []
    alert_ids_seen = set()
    for r in rows:
        try:
            responses = _json_alerts.loads(r["responses"] or "{}")
        except (ValueError, TypeError):
            responses = {}
        aid = int(r["alert_id"]) if r["alert_id"] is not None else None
        if aid is not None:
            alert_ids_seen.add(aid)
        items.append({
            "id": int(r["id"]),
            "alert_id": aid,
            "alert_nom": r["alert_nom"] or "",
            "linked_maint_code": r["linked_maint_code"] or "",
            "operateur": r["user_nom"] or "",
            "machine": r["machine"] or "",
            "no_dossier": r["no_dossier"] or "",
            "ack_at": r["ack_at"],
            "responses": responses,
            "comment": r["comment"] or "",
            "dossier_info": None,
        })

    # ── Enrichissement dossier + fiche technique ────────────────────────────
    # Pour chaque acquittement lié à un dossier (no_dossier renseigné) on va
    # chercher dans planning_entries le contexte du dossier (client, réf produit,
    # format, laize…) et, via ref_produit_norm, dans fiches_techniques les
    # caractéristiques bobine / matière / étiquette. Objectif : afficher ces
    # champs à côté de la tension / qualité serrage saisis par l'opérateur,
    # sans jamais dupliquer la donnée en DB — extraction pure au moment T.
    distinct_dossiers = sorted({(it["no_dossier"] or "").strip() for it in items if (it.get("no_dossier") or "").strip()})
    if distinct_dossiers:
        ph = ",".join(["?"] * len(distinct_dossiers))
        with get_db() as conn3:
            di_rows = conn3.execute(
                f"""SELECT
                      pe.reference          AS reference,
                      pe.numero_of          AS numero_of,
                      pe.client             AS client,
                      pe.description        AS description,
                      pe.ref_produit        AS ref_produit,
                      pe.ref_produit_norm   AS ref_produit_norm,
                      pe.format_l           AS format_l,
                      pe.format_h           AS format_h,
                      pe.laize              AS pe_laize,
                      pe.dos_rvgi           AS dos_rvgi,
                      ft.mandrin_dia        AS mandrin_dia,
                      ft.mandrin_longueur   AS mandrin_longueur,
                      ft.enroulement        AS enroulement,
                      ft.nb_etiq_bobin      AS nb_etiq_bobin,
                      ft.dia_ext            AS dia_ext,
                      ft.poids              AS poids,
                      ft.matiere            AS matiere,
                      ft.adhesif            AS adhesif,
                      ft.support            AS support,
                      ft.glassine           AS glassine,
                      ft.epaisseur          AS epaisseur,
                      ft.laize              AS ft_laize,
                      ft.laize_optimale     AS laize_optimale,
                      ft.eti_laize          AS eti_laize,
                      ft.eti_longueur       AS eti_longueur,
                      ft.eti_rayons         AS eti_rayons,
                      ft.eti_perforations   AS eti_perforations,
                      ft.tete1_anilox       AS tete1_anilox,
                      ft.tete1_composition  AS tete1_composition,
                      ft.machine            AS ft_machine
                    FROM planning_entries pe
                    LEFT JOIN fiches_techniques ft ON ft.id = (
                        SELECT ft2.id FROM fiches_techniques ft2
                        WHERE TRIM(COALESCE(ft2.ref_produit_norm,'')) != ''
                          AND TRIM(ft2.ref_produit_norm) = TRIM(COALESCE(pe.ref_produit_norm,''))
                        ORDER BY
                          CASE WHEN ft2.machine IS NOT NULL AND TRIM(ft2.machine) != '' THEN 0 ELSE 1 END,
                          ft2.id ASC
                        LIMIT 1
                    )
                    WHERE TRIM(pe.reference) IN ({ph})
                       OR TRIM(COALESCE(pe.numero_of,'')) IN ({ph})""",
                tuple(distinct_dossiers) * 2,
            ).fetchall()
        di_map: dict = {}
        for r in di_rows:
            payload = {k: r[k] for k in r.keys()}
            for key_src in ("reference", "numero_of"):
                k = str(r[key_src] or "").strip()
                if not k or k not in distinct_dossiers:
                    continue
                prev = di_map.get(k)
                cur_has_ft = payload.get("mandrin_dia") is not None or payload.get("matiere") is not None
                prev_has_ft = bool(prev) and (prev.get("mandrin_dia") is not None or prev.get("matiere") is not None)
                if prev is None or (cur_has_ft and not prev_has_ft):
                    di_map[k] = payload
        for it in items:
            k = (it.get("no_dossier") or "").strip()
            if k and k in di_map:
                it["dossier_info"] = di_map[k]

    # Charger la structure des questionnaires (points de contrôle) pour les
    # alertes rencontrées, afin que le frontend puisse construire des colonnes
    # dynamiques dans l'historique.
    alerts_meta = {}
    if alert_ids_seen:
        placeholders = ",".join(["?"] * len(alert_ids_seen))
        with get_db() as conn2:
            meta_rows = conn2.execute(
                f"SELECT id, params FROM maintenance_alerts WHERE id IN ({placeholders})",
                tuple(alert_ids_seen),
            ).fetchall()
        for mr in meta_rows:
            try:
                p_json = _json_alerts.loads(mr["params"] or "{}")
            except (ValueError, TypeError):
                p_json = {}
            cl = p_json.get("checklist") or {}
            cl_items = cl.get("items") or []
            clean = []
            if isinstance(cl_items, list):
                for it in cl_items:
                    if isinstance(it, str):
                        clean.append({
                            "label": it, "type": "choice",
                            "responses": ["Conforme"], "multi": True,
                        })
                    elif isinstance(it, dict):
                        entry = {
                            "label": (it.get("label") or "").strip(),
                            "type": (it.get("type") or "choice"),
                        }
                        if entry["type"] == "value":
                            if it.get("unit"):
                                entry["unit"] = it["unit"]
                            if it.get("min") is not None:
                                entry["min"] = it["min"]
                            if it.get("max") is not None:
                                entry["max"] = it["max"]
                        else:
                            entry["responses"] = it.get("responses") or []
                            entry["multi"] = bool(it.get("multi", True))
                            entry["allow_other"] = bool(it.get("allow_other", False))
                            entry["other_is_nc"] = bool(it.get("other_is_nc", False))
                            entry["nc_responses"] = it.get("nc_responses") or []
                        clean.append(entry)
            alerts_meta[str(mr["id"])] = {"checklist_items": clean}

    # ── Toutes les alertes connues (même sans ack) ────────────────────────
    # Objectif : permettre à l'UI "Historique des contrôles" de proposer
    # dans son dropdown de filtre TOUTES les alertes configurées, pas
    # seulement celles qui ont déjà été acquittées. Sans ça, une nouvelle
    # alerte reste "introuvable" tant qu'un opérateur ne l'a pas encore
    # validée.
    known_alerts = []
    try:
        with get_db() as conn4:
            arows = conn4.execute(
                "SELECT id, nom, active, linked_maint_code FROM maintenance_alerts "
                "ORDER BY (linked_maint_code IS NULL), linked_maint_code, id"
            ).fetchall()
        for ar in arows:
            known_alerts.append({
                "id": int(ar["id"]),
                "nom": ar["nom"] or "",
                "active": int(ar["active"] or 0),
                "linked_maint_code": ar["linked_maint_code"] or "",
            })
    except Exception:
        known_alerts = []

    return {"items": items, "alerts_meta": alerts_meta, "known_alerts": known_alerts}


_MAINTENANCE_ALLOWED_IDENTS = {"loic.gognau"}


def _require_maintenance_access(request: Request) -> dict:
    """Mêmes règles d'accès que la page /maintenance : superadmin ou identifiant
    figurant dans la liste blanche. Utilisé pour autoriser la suppression
    d'historique (correction d'erreurs de saisie)."""
    user = get_current_user(request)
    if user.get("role") == ROLE_SUPERADMIN:
        return user
    ident = str(user.get("identifiant") or "").strip().lower()
    if ident in _MAINTENANCE_ALLOWED_IDENTS:
        return user
    raise HTTPException(status_code=403, detail="Accès maintenance réservé.")


@router.delete("/api/maintenance/alert-acks/{ack_id}")
def maintenance_alert_acks_delete(ack_id: int, request: Request):
    """Suppression d'une ligne d'historique d'acquittement. Utilisé pour
    corriger les erreurs de saisie côté opérateur. Le last_ack_at de l'alerte
    n'est PAS recalculé automatiquement (il pointe sur la dernière entrée
    présente, dont la valeur ne bouge pas en supprimant des entrées plus
    anciennes ; pour la dernière, on le réajuste à la nouvelle MAX(ack_at)
    restante par alerte/machine)."""
    user = _require_maintenance_access(request)
    from database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, alert_id, machine FROM maintenance_alert_acks WHERE id=?",
            (ack_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Acquittement introuvable.")
        alert_id_val = row["alert_id"]
        machine_val = row["machine"]
        conn.execute("DELETE FROM maintenance_alert_acks WHERE id=?", (ack_id,))
        # Recalcule last_ack_at sur l'alerte à partir de ce qu'il reste
        new_last = conn.execute(
            "SELECT MAX(ack_at) AS m FROM maintenance_alert_acks WHERE alert_id=?",
            (alert_id_val,),
        ).fetchone()
        new_last_val = new_last["m"] if new_last else None
        now_paris = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            "UPDATE maintenance_alerts SET last_ack_at=?, updated_at=? WHERE id=?",
            (new_last_val, now_paris, alert_id_val),
        )
        conn.commit()
    log_action(user=user, action="DELETE", module="maintenance_alerts",
               objet="ack:" + str(ack_id),
               detail=f"alert_id={alert_id_val} machine={machine_val}")
    return {"ok": True}


def _auto_ack_periodic_alerts_on_arret(conn, user, machine, no_dossier, code, code_label, operation_str):
    """v2.2.65 — Ferme automatiquement toutes les alertes périodiques actives dont la
    target couvre cette machine, quand l'opérateur saisit un code non-productif
    (arrêt, pause, calage, technique, fin dossier — tout sauf 01 et 03).

    Une ligne est insérée dans maintenance_alert_acks pour chaque alerte avec le
    motif dans le champ comment. Effet : compteur périodique reset, plus de lignes
    vierges dans l'historique, modales à l'écran se ferment au prochain polling.
    """
    if not machine:
        return
    from database import get_db  # noqa: F401 (import garde le style existant)
    now_paris = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        rows = conn.execute(
            "SELECT id, params FROM maintenance_alerts WHERE active=1"
        ).fetchall()
    except Exception:
        return
    if code_label:
        reason = f"Fermée auto : {code} – {code_label}"
    else:
        reason = f"Fermée auto : code {code}"
    reason = reason[:2000]
    user_id = user.get("id") if user else None
    user_nom = (user.get("nom") if user else "") or (user.get("email") if user else "") or ""
    responses_json = "{}"
    for r in rows:
        try:
            params = _json_alerts.loads(r["params"] or "{}")
        except (ValueError, TypeError):
            continue
        trig = params.get("trigger") or {}
        if trig.get("type") != "periodic":
            continue
        target = params.get("target") or {}
        machines_target = target.get("machines")
        if not isinstance(machines_target, list) or not machines_target:
            legacy = target.get("machine")
            machines_target = [legacy] if isinstance(legacy, str) and legacy else ["*"]
        if "*" not in machines_target and machine not in machines_target:
            continue
        try:
            conn.execute(
                """INSERT INTO maintenance_alert_acks
                   (alert_id, user_id, user_nom, machine, no_dossier,
                    ack_at, responses, comment)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (int(r["id"]), user_id, user_nom, machine, no_dossier or "",
                 now_paris, responses_json, reason),
            )
            conn.execute(
                "UPDATE maintenance_alerts SET last_ack_at=?, updated_at=? WHERE id=?",
                (now_paris, now_paris, int(r["id"])),
            )
        except Exception:
            continue
    try:
        conn.commit()
    except Exception:
        pass


@router.post("/api/maintenance/alerts/{alert_id}/ack")
async def maintenance_alerts_ack(alert_id: int, request: Request):
    """Acquittement opérateur d'une alerte. Enregistre l'historique et met
    à jour last_ack_at sur l'alerte pour réinitialiser le compteur périodique."""
    user = get_current_user(request)
    body = await request.json()
    responses = body.get("responses") or {}
    if not isinstance(responses, dict):
        responses = {}
    comment = (body.get("comment") or "").strip()
    if len(comment) > 2000:
        comment = comment[:2000]
    no_dossier = (body.get("no_dossier") or "").strip()
    from database import get_db
    now_paris = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        # Vérifier que l'alerte existe et est active
        row = conn.execute(
            "SELECT id, active FROM maintenance_alerts WHERE id=?", (alert_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Alerte introuvable.")
        # Machine de l'opérateur (ou vide pour superadmin sans machine)
        machine = _machine_name_from_user(conn, user) or ""
        # v163+ : fallback serveur robuste — si le client n'a pas transmis de
        # no_dossier (super admin sans opérateur lié, opérateur qui n'a pas
        # /prod ouvert, etc.), on cherche le dernier dossier touché sur cette
        # machine dans les 30 dernières minutes avant l'ack. C'est la sémantique
        # « atelier » : l'ack est daté à un instant T, on regarde ce qui se
        # passait sur cette machine juste avant.
        if not no_dossier and machine:
            window_start = (datetime.now(ZoneInfo("Europe/Paris"))
                            - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S")
            recent_dos = conn.execute(
                """SELECT no_dossier FROM production_data
                   WHERE machine=?
                     AND date_operation >= ?
                     AND no_dossier IS NOT NULL AND TRIM(no_dossier) != ''
                   ORDER BY date_operation DESC LIMIT 1""",
                (machine, window_start),
            ).fetchone()
            if recent_dos and recent_dos["no_dossier"]:
                no_dossier = str(recent_dos["no_dossier"]).strip()
        try:
            responses_json = _json_alerts.dumps(responses, ensure_ascii=False)
        except (TypeError, ValueError):
            responses_json = "{}"
        conn.execute(
            """INSERT INTO maintenance_alert_acks
               (alert_id, user_id, user_nom, machine, no_dossier,
                ack_at, responses, comment)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (alert_id, user.get("id"), user.get("nom") or user.get("email") or "",
             machine, no_dossier, now_paris, responses_json, comment),
        )
        # Met à jour le last_ack_at sur l'alerte (cache utilisé en /settings)
        conn.execute(
            "UPDATE maintenance_alerts SET last_ack_at=?, updated_at=? WHERE id=?",
            (now_paris, now_paris, alert_id),
        )
        conn.commit()
    log_action(user=user, action="VALIDATE", module="maintenance_alerts",
               objet=str(alert_id),
               detail=f"machine={machine} dossier={no_dossier} comment_len={len(comment)}")
    return {"ok": True, "ack_at": now_paris}


@router.post("/api/maintenance/alerts/{alert_id}/dismiss")
async def maintenance_alerts_dismiss(alert_id: int, request: Request):
    """Fermeture silencieuse d'une alerte par l'opérateur.

    v164 : contrairement à /ack, cet endpoint :
    - N'insère rien de visible dans l'historique des contrôles (dismissed=1)
    - N'est pas tracé dans les audit_logs
    - Ne stocke aucune réponse/commentaire
    - Mais bloque quand même l'alerte jusqu'au prochain trigger (89) via la
      colonne dismissed qui reste comptée dans MAX(ack_at) côté logique event.

    L'opérateur peut esquiver une alerte non pertinente sans polluer la qualité.
    Le bouton n'apparaît que si params.dismiss_button.enabled=True.
    """
    user = get_current_user(request)
    from database import get_db
    now_paris = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, params FROM maintenance_alerts WHERE id=?", (alert_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Alerte introuvable.")
        # Vérifie que le bouton dismiss est bien activé pour cette alerte
        try:
            params = _json_alerts.loads(row["params"] or "{}")
        except (ValueError, TypeError):
            params = {}
        dismiss = params.get("dismiss_button") or {}
        if not (isinstance(dismiss, dict) and dismiss.get("enabled")):
            raise HTTPException(403, "Fermeture non autorisée pour cette alerte.")
        machine = _machine_name_from_user(conn, user) or ""
        conn.execute(
            """INSERT INTO maintenance_alert_acks
               (alert_id, user_id, user_nom, machine, no_dossier,
                ack_at, responses, comment, dismissed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (alert_id, user.get("id"), user.get("nom") or user.get("email") or "",
             machine, "", now_paris, "{}", ""),
        )
        conn.execute(
            "UPDATE maintenance_alerts SET last_ack_at=?, updated_at=? WHERE id=?",
            (now_paris, now_paris, alert_id),
        )
        conn.commit()
    # Pas de log_action volontairement — l'esquive doit être invisible.
    return {"ok": True, "dismissed": True}


@router.get("/api/maintenance/wearparts/last")
def maintenance_wearparts_last(request: Request, machine: str = ""):
    """Dernières opérations couteaux pour une machine."""
    get_current_user(request)
    machine = (machine or "").strip()
    if not machine:
        raise HTTPException(422, "Param 'machine' requis.")
    from database import get_db
    queries = [
        ("couteaux_bande",         "%couteaux%bande%", "%contre%couteaux%bande%"),
        ("couteaux_rive",          "%couteaux%rive%",  "%contre%couteaux%rive%"),
        ("contre_couteaux_bande",  "%contre%couteaux%bande%", None),
        ("contre_couteaux_rive",   "%contre%couteaux%rive%",  None),
    ]
    items = {}
    with get_db() as conn:
        m_row = conn.execute(
            "SELECT dernier_metrage FROM machines WHERE nom=? AND actif=1 LIMIT 1",
            (machine,),
        ).fetchone()
        current_metrage = m_row["dernier_metrage"] if m_row else None
        for key, pat, exclude in queries:
            sql = "SELECT date_operation FROM production_data WHERE machine=? AND LOWER(operation) LIKE LOWER(?)"
            params = [machine, pat]
            if exclude:
                sql += " AND LOWER(operation) NOT LIKE LOWER(?)"
                params.append(exclude)
            sql += " ORDER BY date_operation DESC LIMIT 1"
            row = conn.execute(sql, params).fetchone()
            if not row or not row["date_operation"]:
                items[key] = {"last_date": None, "metrage_at_change": None, "metrage_since": None}
                continue
            change_date = row["date_operation"]
            m_at_row = conn.execute(
                "SELECT COALESCE(metrage_total_fin, metrage_total_debut) AS m FROM production_data "
                "WHERE machine=? AND operation_code IN ('01','89') AND date_operation <= ? "
                "AND (metrage_total_fin IS NOT NULL OR metrage_total_debut IS NOT NULL) "
                "ORDER BY date_operation DESC, id DESC LIMIT 1",
                (machine, change_date),
            ).fetchone()
            m_at_change = m_at_row["m"] if m_at_row else None
            metrage_since = None
            if current_metrage is not None and m_at_change is not None:
                try:
                    metrage_since = max(0.0, float(current_metrage) - float(m_at_change))
                except (TypeError, ValueError):
                    metrage_since = None
            items[key] = {"last_date": change_date, "metrage_at_change": m_at_change, "metrage_since": metrage_since}
    dates = {k: v["last_date"] for k, v in items.items()}
    return {"machine": machine, "current_metrage": current_metrage, "dates": dates, "items": items}


@router.post("/api/maintenance/wearparts/info")
async def maintenance_wearparts_info(request: Request):
    """Métrage machine et parcouru depuis une date par pièce."""
    get_current_user(request)
    body = await request.json()
    machine = (body.get("machine") or "").strip()
    if not machine:
        raise HTTPException(422, "machine requis.")
    raw_dates = body.get("dates") or {}
    if not isinstance(raw_dates, dict):
        raise HTTPException(422, "dates doit etre un objet.")
    from database import get_db
    items = {}
    with get_db() as conn:
        m_row = conn.execute(
            "SELECT dernier_metrage FROM machines WHERE nom=? AND actif=1 LIMIT 1",
            (machine,),
        ).fetchone()
        current_metrage = m_row["dernier_metrage"] if m_row else None
        for key, change_date in raw_dates.items():
            if not change_date:
                items[key] = {"last_date": None, "metrage_at_change": None, "metrage_since": None}
                continue
            change_date = str(change_date)
            m_at_row = conn.execute(
                "SELECT COALESCE(metrage_total_fin, metrage_total_debut) AS m FROM production_data "
                "WHERE machine=? AND operation_code IN ('01','89') AND date_operation <= ? "
                "AND (metrage_total_fin IS NOT NULL OR metrage_total_debut IS NOT NULL) "
                "ORDER BY date_operation DESC, id DESC LIMIT 1",
                (machine, change_date),
            ).fetchone()
            m_at_change = m_at_row["m"] if m_at_row else None
            metrage_since = None
            if current_metrage is not None and m_at_change is not None:
                try:
                    metrage_since = max(0.0, float(current_metrage) - float(m_at_change))
                except (TypeError, ValueError):
                    metrage_since = None
            items[key] = {"last_date": change_date, "metrage_at_change": m_at_change, "metrage_since": metrage_since}
    return {"machine": machine, "current_metrage": current_metrage, "items": items}
