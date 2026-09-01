"""Paramètres & matrice d'accès — accès par section (config.ROLES_SETTINGS_*)."""

import hashlib
import re
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
    ROLE_LABELS,
    ACCESS_LEVELS,
    LEVEL_LABELS,
    LEVEL_ORDER,
    is_known_app_module,
)
from app.services.audit_service import log_action
from app.services.maint_op_merge import merge_op_rows
from services.auth_service import (
    get_current_user,
    require_settings,
    is_real_superadmin,
    merged_app_access,
    parse_access_overrides_raw,
)

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

# Déplacé dans config.py (source de vérité) : le gestionnaire de tâches affiche
# les mêmes libellés, deux dictionnaires auraient divergé au premier rôle ajouté.
_ROLE_LABELS = ROLE_LABELS


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
    actor = require_settings(request)
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
        # Rôles que CET utilisateur peut attribuer en créant / modifiant un
        # compte. Un non super admin ne peut pas se fabriquer une direction :
        # le back le refuse (auth._guard_role_attribuable), le select le
        # reflète pour ne pas proposer un choix qui finirait en 403.
        "roles_assignables": sorted(
            (ASSIGNABLE_ROLES | {ROLE_SUPERADMIN})
            if is_real_superadmin(actor)
            else (ASSIGNABLE_ROLES - {ROLE_DIRECTION, ROLE_SUPERADMIN})
        ),
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
        user=admin_user,
        request=request,
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
        user=admin_user,
        request=request,
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


@router.get("/api/settings/audit/facets")
def get_audit_facets(request: Request):
    """Modules et actions REELLEMENT presents dans le journal.

    Les listes deroulantes du journal etaient ecrites en dur dans la page : 8
    modules et 7 actions, quand le code en emettait deja 15 et 17. MyAO, la
    memoire produit et toute la maintenance n'etaient donc filtrables nulle
    part. On les construit desormais a partir des donnees, habillees par la
    taxonomie — ajouter un module ne demande plus de toucher a la page.
    """
    require_settings(request)
    from database import get_db
    from app.core.audit_taxonomy import action_color, action_label, module_label

    with get_db() as conn:
        modules = [
            r[0] for r in conn.execute(
                "SELECT module FROM audit_logs WHERE module IS NOT NULL AND module <> '' "
                "GROUP BY module"
            ).fetchall()
        ]
        actions = [
            r[0] for r in conn.execute(
                "SELECT action FROM audit_logs WHERE action IS NOT NULL AND action <> '' "
                "GROUP BY action"
            ).fetchall()
        ]

    return {
        "modules": sorted(
            ({"value": m, "label": module_label(m)} for m in modules),
            key=lambda d: d["label"].lower(),
        ),
        "actions": sorted(
            (
                {"value": a, "label": action_label(a), "color": action_color(a)}
                for a in actions
            ),
            key=lambda d: d["label"].lower(),
        ),
    }


@router.get("/api/settings/audit/couverture")
def get_audit_couverture(request: Request):
    """Ce que le journal couvre, appli par appli.

    La question « qu'est-ce qui alimente le journal ? » n'avait aucune reponse
    consultable : il fallait ouvrir les routers. Cet endpoint la donne depuis
    l'application VIVANTE — il parcourt les routes reellement enregistrees par
    FastAPI, pas une liste tenue a la main. Ajouter un endpoint le fait
    apparaitre ici au redemarrage suivant, sans que personne ait rien a mettre
    a jour.

    Trois choses sont renvoyees :

    - `applis` : par module, les verbes d'action journalisables, le nombre de
      routes d'ecriture derriere chaque verbe, et ce qui a REELLEMENT ete
      enregistre (nombre d'entrees, derniere en date) ;
    - `exclues` : les routes volontairement hors journal (battements de coeur,
      agent d'impression, releves de fluidite, abonnements push). Les montrer
      evite la question « pourquoi celle-la n'apparait jamais ? » ;
    - les totaux, pour situer d'un coup d'oeil.

    Un module present en base mais sans route (module renomme, endpoint retire)
    reste liste : son historique existe et doit rester filtrable.
    """
    require_settings(request)
    from database import get_db
    from app.core.audit_taxonomy import (
        action_color,
        action_label,
        is_skipped,
        module_label,
        resolve_action,
        resolve_module,
        routes_ecriture,
    )

    applis: dict = {}

    def _appli(module: str) -> dict:
        return applis.setdefault(
            module,
            {
                "module": module,
                "label": module_label(module),
                "routes": 0,
                "entrees": 0,
                "derniere": None,
                "actions": {},
            },
        )

    def _action(appli: dict, code: str) -> dict:
        return appli["actions"].setdefault(
            code,
            {
                "action": code,
                "label": action_label(code),
                "color": action_color(code),
                "routes": 0,
                "entrees": 0,
                "derniere": None,
            },
        )

    hors_journal: dict = {}
    for methode, chemin in routes_ecriture(request.app):
        if is_skipped(chemin):
            hors_journal.setdefault(chemin, set()).add(methode)
            continue
        appli = _appli(resolve_module(chemin))
        appli["routes"] += 1
        _action(appli, resolve_action(methode, chemin))["routes"] += 1
    exclues = [
        {"chemin": c, "methodes": sorted(m)} for c, m in hors_journal.items()
    ]

    # Ce qui a ete reellement enregistre, module par module et verbe par verbe.
    with get_db() as conn:
        lignes = conn.execute(
            """SELECT module, action, COUNT(*) AS n, MAX(created_at) AS derniere
                 FROM audit_logs
                WHERE module IS NOT NULL AND module <> ''
                GROUP BY module, action"""
        ).fetchall()

    for ligne in lignes:
        appli = _appli(ligne["module"])
        act = _action(appli, (ligne["action"] or "").upper())
        brut = ligne["derniere"] or ""
        act["entrees"] = ligne["n"]
        act["derniere"] = _audit_created_at_display_paris(brut) if brut else None
        appli["entrees"] += ligne["n"]
        # Les horodatages sont en ISO : la comparaison de chaines suffit a
        # trouver le plus recent, sans repasser par un parse de date.
        if brut > appli.get("_brut", ""):
            appli["_brut"] = brut
            appli["derniere"] = act["derniere"]

    sortie = []
    for appli in applis.values():
        appli.pop("_brut", None)
        appli["actions"] = sorted(
            appli["actions"].values(), key=lambda a: a["label"].lower()
        )
        sortie.append(appli)
    sortie.sort(key=lambda a: a["label"].lower())

    exclues.sort(key=lambda e: e["chemin"])
    return {
        "applis": sortie,
        "exclues": exclues,
        "total_routes": sum(a["routes"] for a in sortie),
        "total_entrees": sum(a["entrees"] for a in sortie),
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
            # ── Champs FSC : absents de ce SELECT jusqu'ici ────────────────
            # `fsc_date_expiration`, `sous_traitant` et `categories` existent
            # en base (migrations 209 et 213) et l'interface les édite déjà —
            # mais l'API ne les renvoyait pas et ne les écrivait pas. Trois
            # conséquences silencieuses : la case « Sous-traitant » se perdait
            # au rechargement, les catégories aussi, et surtout le badge
            # « Certificat FSC expire le… » (settings_page.py) ne s'est jamais
            # affiché puisque la donnée n'arrivait jamais au front.
            #
            # La validité du certificat À LA DATE DU BL est une exigence de
            # chaîne de contrôle : sans cette colonne, aucun contrôle possible.
            # ── siret / tva_intracom : créés par la migration 214, édités et
            # affichés par la fiche v2 depuis le premier jour… mais absents de
            # ce SELECT, de l'INSERT et de l'UPDATE. Les deux champs étaient
            # donc toujours vides à l'écran et jamais persistés : on saisissait
            # un SIRET, on sauvegardait, il disparaissait sans message.
            #
            # ── telephone / email / fax / conditions d'achat / regime_tva /
            # rcs : ajoutés par la migration `fournisseur_contact_conditions`.
            """SELECT ff.id, ff.nom, ff.licence, ff.certificat, ff.has_fsc,
                      ff.fsc_date_expiration, ff.sous_traitant, ff.categories,
                      ff.traca_photo_url, ff.traca_explication, ff.traca_exemple_code,
                      ff.groupe, ff.branche,
                      ff.adresse, ff.code_postal, ff.ville, ff.pays,
                      ff.langue_default, ff.tags, ff.notes, ff.actif, ff.updated_at,
                      ff.siret, ff.tva_intracom, ff.price_currency,
                      ff.telephone, ff.email, ff.fax,
                      ff.mode_reglement, ff.mode_livraison, ff.delai_expedition_jours,
                      ff.regime_tva, ff.rcs,
                      -- Lien vers la fiche RVGI. Ce SELECT est explicite : une
                      -- colonne absente d'ici n'atteint jamais l'écran, et c'est
                      -- déjà arrivé deux fois (voir plus haut).
                      ff.rvgi_numero, ff.rvgi_code, ff.rvgi_etat, ff.rvgi_motif,
                      ff.rvgi_score, ff.rvgi_bloq, ff.rvgi_rs, ff.rvgi_groupe,
                      ff.rvgi_lie_le, ff.rvgi_maj_le,
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
        # `categories` est stocké en JSON (migration 213). Le front attend une
        # liste ; on la lui donne parsée plutôt que de lui faire deviner.
        raw_cat = d.get("categories")
        if raw_cat:
            try:
                parsed_c = json.loads(raw_cat)
                d["categories"] = parsed_c if isinstance(parsed_c, list) else []
            except (json.JSONDecodeError, TypeError):
                d["categories"] = []
        else:
            d["categories"] = []
        d["sous_traitant"] = int(d.get("sous_traitant") or 0)
        out.append(d)
    return out


@router.get("/api/fournisseurs/categories")
def list_fournisseur_categories(request: Request):
    """Référentiel des catégories fournisseurs (source de vérité du front).

    Déclaré avant les routes paramétrées `/api/fournisseurs/{...}` pour ne
    pas être capté par un segment variable.
    """
    require_settings(request)
    from config import fournisseur_categories
    return fournisseur_categories()


@router.get("/api/fournisseurs/picker")
def fournisseurs_picker(request: Request):
    """Annuaire allégé pour la recherche fournisseur (MysFournisseurPicker).

    Source UNIQUE de tous les champs « fournisseur » de l'application. Avant,
    chaque écran avait le sien : `/api/stock/fournisseurs`, `/api/fabrication/
    fournisseurs-fsc`, `/api/pricing/fournisseurs`, `/api/ao/picker/
    fournisseurs`, plus deux listes codées en dur côté client. Six vérités pour
    un annuaire, avec des divergences réelles — `has_fsc` valait 1 par défaut
    ici et 0 là.

    Garde : `get_current_user`, pas `require_settings`. Un opérateur qui
    réceptionne une bobine doit pouvoir désigner son fournisseur sans être
    administrateur ; c'est bien le seul point commun de tous les appelants.

    Charge utile réduite à ce que la recherche affiche ou interroge — ni
    notes, ni traçabilité, ni dates de certificat : cette liste est
    téléchargée à l'ouverture de chaque page qui contient un tel champ.
    """
    get_current_user(request)
    from database import get_db
    from config import fournisseur_categories
    import json as _json
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, nom, categories, has_fsc, licence, certificat,
                      code_postal, ville, pays, groupe, branche, tags, email, actif
                 FROM fournisseurs_fsc
                ORDER BY nom COLLATE NOCASE ASC"""
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for champ in ("categories", "tags"):
            brut = d.get(champ)
            if brut:
                try:
                    p = _json.loads(brut)
                    d[champ] = p if isinstance(p, list) else []
                except (_json.JSONDecodeError, TypeError):
                    d[champ] = []
            else:
                d[champ] = []
        d["has_fsc"] = 1 if d.get("has_fsc") else 0
        d["actif"] = 1 if (d.get("actif") is None or d.get("actif")) else 0
        out.append(d)
    # Le référentiel voyage avec la liste : le picker doit nommer le groupe
    # « Fournisseurs adhésif » sans un second aller-retour réseau.
    return {"fournisseurs": out, "categories": fournisseur_categories()}


@router.get("/api/fournisseurs/referentiels-achat")
def list_referentiels_achat(request: Request):
    """Modes de règlement, modes de livraison, régimes de TVA.

    Trois référentiels de `config.py`, servis ensemble : la fiche fournisseur
    les affiche dans le même bloc, un appel par liste serait trois requêtes
    pour trois constantes.
    """
    get_current_user(request)
    from config import modes_reglement, modes_livraison, regimes_tva
    return {
        "modes_reglement": modes_reglement(),
        "modes_livraison": modes_livraison(),
        "regimes_tva": regimes_tva(),
    }


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


# ═══════════════════════════════════════════════════════════════════════
# Certifications fournisseurs — miroir de MyQualité › Ressources
# fournisseurs. AUCUNE table nouvelle : on lit `qualite_ref_fiches`
# (catalogue du référentiel RSE), `qualite_fournisseur_certificats`
# (documents déposés) et `qualite_fournisseur_certificat_fiches` (le
# tag document → certification). Le dépôt et l'édition restent dans
# MyQualité : ici c'est lecture seule.
#
# Règle héritée de MyQualité et rendue visible dans la fiche : un
# certificat portant `groupe_ref` couvre TOUTES les branches du groupe,
# pas seulement celle qui l'a téléversé.
# ═══════════════════════════════════════════════════════════════════════

# Ordre de préséance quand deux documents couvrent la même certification :
# le meilleur statut gagne. Identique à _COUV_RANG dans routers/qualite.py.
_FOUR_CERT_RANG = {"valide": 0, "soon": 1, "nod": 2, "exp": 3}


def _four_cert_statut(date_expiration):
    """'valide' | 'soon' (<=60 j) | 'exp' | 'nod' (pas de date).

    Mêmes seuils que _compute_cert_status (routers/qualite.py) — les deux
    écrans doivent afficher le même statut pour le même document.
    """
    if not date_expiration:
        return "nod"
    try:
        dexp = datetime.strptime(str(date_expiration)[:10], "%Y-%m-%d").date()
    except Exception:
        return "nod"
    today = datetime.now().date()
    if dexp < today:
        return "exp"
    return "soon" if (dexp - today).days <= 60 else "valide"


def _four_load_referentiel(conn):
    """Catalogue des certifications (qualite_ref_fiches).

    Renvoie [] si la table n'existe pas encore — le module Qualité peut ne
    pas être initialisé sur une base fraîche, et l'onglet Certifications
    doit alors se dégrader proprement au lieu de casser la page entière.
    """
    try:
        rows = conn.execute(
            """SELECT id, slug, nom, acronyme, categorie, statut_sifa
               FROM qualite_ref_fiches
               ORDER BY categorie ASC, nom COLLATE NOCASE ASC"""
        ).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


def _four_load_couverture(conn):
    """Couverture par fournisseur : {fournisseur_id: {fiche_id: entry}}.

    entry = {statut, niveau ('branche'|'groupe'), titre, date_expiration,
             certificat_id, filename}
    """
    try:
        certs = conn.execute(
            """SELECT id, fournisseur_id, titre, original_name,
                      date_emission, date_expiration, groupe_ref
               FROM qualite_fournisseur_certificats"""
        ).fetchall()
        liens = conn.execute(
            "SELECT certificat_id, fiche_id FROM qualite_fournisseur_certificat_fiches"
        ).fetchall()
    except Exception:
        return {}, {}

    meta = {c["id"]: dict(c) for c in certs}

    # groupe (minuscule) -> [fournisseur_id...] : cible d'un certificat groupe
    par_groupe = {}
    for r in conn.execute(
        """SELECT id, groupe FROM fournisseurs_fsc
           WHERE groupe IS NOT NULL AND TRIM(groupe) <> ''"""
    ).fetchall():
        par_groupe.setdefault(r["groupe"].strip().lower(), []).append(r["id"])

    couv = {}

    def _pose(fid, fiche_id, entry):
        if fid is None:
            return
        d = couv.setdefault(fid, {})
        cur = d.get(fiche_id)
        if cur is None or _FOUR_CERT_RANG.get(entry["statut"], 9) < _FOUR_CERT_RANG.get(cur["statut"], 9):
            d[fiche_id] = entry

    for lk in liens:
        m = meta.get(lk["certificat_id"])
        if not m:
            continue
        gref = (m.get("groupe_ref") or "").strip().lower()
        cibles = par_groupe.get(gref) if gref else None
        entry_base = {
            "statut": _four_cert_statut(m.get("date_expiration")),
            "niveau": "groupe" if cibles else "branche",
            "titre": m.get("titre") or m.get("original_name") or "",
            "date_emission": m.get("date_emission"),
            "date_expiration": m.get("date_expiration"),
            "certificat_id": m["id"],
            "filename": m.get("original_name") or "",
            "groupe_ref": m.get("groupe_ref") or None,
        }
        for fid in (cibles or [m["fournisseur_id"]]):
            _pose(fid, lk["fiche_id"], dict(entry_base))

    return couv, meta


def _four_stats_couverture(entries, total_referentiel):
    s = {"couvert": 0, "valide": 0, "soon": 0, "exp": 0, "nod": 0,
         "total": total_referentiel}
    for e in (entries or {}).values():
        s["couvert"] += 1
        s[e["statut"]] = s.get(e["statut"], 0) + 1
    return s


# ─── Date d'expiration FSC : le document déposé fait foi ─────────────
#
# La date vivait à deux endroits : `fournisseurs_fsc.fsc_date_expiration`
# (saisie à la main dans les Paramètres) et le certificat PDF déposé dans
# MyQualité, qui porte sa propre `date_expiration`. Deux saisies, deux
# chances de diverger — et c'est arrivé (badge « échéance inconnue » alors
# que le certificat déposé était valide jusqu'en 2027).
#
# Règle retenue : le document fait foi. La colonne reste écrite parce que
# tout l'aval la lit (contrôle au BL, registre FSC), mais elle devient
# DÉRIVÉE — resynchronisée depuis le document, plus saisie.

def _four_fiche_fsc_id(ref):
    """id de la fiche « FSC » dans le référentiel RSE, ou None."""
    for r in ref:
        if (r.get("slug") or "").strip().lower() == "fsc":
            return r["id"]
    for r in ref:
        if (r.get("acronyme") or "").strip().upper() == "FSC":
            return r["id"]
    return None


def _four_fsc_doc(entries, fiche_fsc_id):
    """Entrée de couverture correspondant au certificat FSC, ou None."""
    if not fiche_fsc_id:
        return None
    return (entries or {}).get(fiche_fsc_id)


def _four_sync_fsc_dates(conn, ref, couv, only_id=None):
    """Aligne fsc_date_expiration sur la date du certificat FSC déposé.

    N'écrit que s'il y a une différence, et jamais dans l'autre sens : un
    fournisseur sans certificat déposé garde sa date saisie à la main.
    Renvoie la liste des changements pour le journal d'audit.
    """
    fiche_id = _four_fiche_fsc_id(ref)
    if not fiche_id:
        return []
    q = "SELECT id, nom, fsc_date_expiration, has_fsc FROM fournisseurs_fsc"
    params = ()
    if only_id is not None:
        q += " WHERE id=?"
        params = (only_id,)
    changes = []
    for row in conn.execute(q, params).fetchall():
        doc = _four_fsc_doc(couv.get(row["id"]), fiche_id)
        if not doc or not doc.get("date_expiration"):
            continue
        avant = row["fsc_date_expiration"]
        apres = str(doc["date_expiration"])[:10]
        if avant == apres:
            continue
        conn.execute(
            "UPDATE fournisseurs_fsc SET fsc_date_expiration=? WHERE id=?",
            (apres, row["id"]),
        )
        changes.append({"id": row["id"], "nom": row["nom"],
                        "avant": avant, "apres": apres,
                        "certificat_id": doc.get("certificat_id"),
                        "niveau": doc.get("niveau")})
    if changes:
        conn.commit()
    return changes


@router.post("/api/fournisseurs/sync-fsc-certificats")
def sync_fsc_certificats(request: Request):
    """Resynchronise les dates d'expiration FSC depuis les certificats déposés.

    Appelé silencieusement à l'ouverture de l'onglet Fournisseurs, et
    disponible en bouton pour voir le rapport. Idempotent.
    """
    user = require_settings(request)
    from database import get_db
    with get_db() as conn:
        ref = _four_load_referentiel(conn)
        couv, _meta = _four_load_couverture(conn)
        changes = _four_sync_fsc_dates(conn, ref, couv)
    if changes:
        log_action(
            user=user,
            action="UPDATE",
            module="settings",
            objet=f"Sync FSC depuis certificats ({len(changes)})",
            detail={"changes": changes},
            ip=request.client.host if request.client else None,
        )
    return {"success": True, "updated": changes, "count": len(changes)}


@router.get("/api/fournisseurs/referentiel-certifications")
def list_referentiel_certifications(request: Request):
    """Catalogue du référentiel RSE + couverture agrégée de chaque fournisseur.

    Un seul appel pour peindre la colonne « Certifications » de la liste :
    32 fournisseurs × N certifications en une requête plutôt qu'un aller-retour
    par ligne.

    Déclaré avant les routes paramétrées `/api/fournisseurs/{...}` pour ne pas
    être capté par un segment variable.
    """
    require_settings(request)
    from database import get_db
    with get_db() as conn:
        ref = _four_load_referentiel(conn)
        couv, _meta = _four_load_couverture(conn)
        ids = [r["id"] for r in conn.execute("SELECT id FROM fournisseurs_fsc").fetchall()]

    fiche_fsc = _four_fiche_fsc_id(ref)
    by_id = {r["id"]: r for r in ref}
    out = {}
    for fid in ids:
        entries = couv.get(fid, {})
        st = _four_stats_couverture(entries, len(ref))
        doc_fsc = _four_fsc_doc(entries, fiche_fsc)
        # Les 3 acronymes les plus « sains » d'abord : c'est ce que la
        # cellule de liste affiche avant le « +N ».
        top = sorted(
            (
                {
                    "fiche_id": k,
                    "acronyme": (by_id.get(k, {}).get("acronyme")
                                 or by_id.get(k, {}).get("nom") or "?"),
                    "statut": v["statut"],
                    "niveau": v["niveau"],
                }
                for k, v in entries.items() if k in by_id
            ),
            key=lambda x: (_FOUR_CERT_RANG.get(x["statut"], 9), x["acronyme"]),
        )
        out[str(fid)] = {"stats": st, "top": top, "fsc_doc": doc_fsc}
    return {"referentiel": ref, "couverture": out, "fiche_fsc_id": fiche_fsc}


@router.get("/api/fournisseurs/{fournisseur_id}/certifications")
def fournisseur_certifications(fournisseur_id: int, request: Request):
    """Détail Certifications d'un fournisseur : catalogue + couverture + documents.

    `documents` contient ses propres certificats ET ceux déposés au niveau de
    son groupe : ces derniers portent niveau='groupe' et ne sont pas stockés
    sur lui — ils s'affichent parce qu'ils le couvrent.
    """
    require_settings(request)
    from database import get_db
    with get_db() as conn:
        four = conn.execute(
            "SELECT id, nom, groupe, branche FROM fournisseurs_fsc WHERE id=?",
            (fournisseur_id,),
        ).fetchone()
        if not four:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        ref = _four_load_referentiel(conn)
        couv, meta = _four_load_couverture(conn)
        try:
            liens = conn.execute(
                """SELECT l.certificat_id, l.fiche_id, f.nom, f.acronyme
                   FROM qualite_fournisseur_certificat_fiches l
                   JOIN qualite_ref_fiches f ON f.id = l.fiche_id"""
            ).fetchall()
        except Exception:
            liens = []

    groupe = (four["groupe"] or "").strip().lower()
    fiches_par_cert = {}
    for lk in liens:
        fiches_par_cert.setdefault(lk["certificat_id"], []).append(
            {"fiche_id": lk["fiche_id"], "nom": lk["nom"], "acronyme": lk["acronyme"]}
        )

    documents = []
    for cid, m in meta.items():
        gref = (m.get("groupe_ref") or "").strip().lower()
        est_groupe = bool(gref)
        # Retenu si c'est un document de ce fournisseur, ou un document
        # groupe portant le groupe auquel il est rattaché.
        if not (m["fournisseur_id"] == fournisseur_id or (est_groupe and gref and gref == groupe)):
            continue
        documents.append({
            "id": cid,
            "titre": m.get("titre") or m.get("original_name") or "",
            "filename": m.get("original_name") or "",
            "date_emission": m.get("date_emission"),
            "date_expiration": m.get("date_expiration"),
            "statut": _four_cert_statut(m.get("date_expiration")),
            "niveau": "groupe" if est_groupe else "branche",
            "fiches": fiches_par_cert.get(cid, []),
        })
    documents.sort(key=lambda d: (d["niveau"] != "branche", d["titre"].lower()))

    entries = couv.get(fournisseur_id, {})
    fiche_fsc = _four_fiche_fsc_id(ref)
    return {
        "fournisseur": dict(four),
        "referentiel": ref,
        "couverture": {str(k): v for k, v in entries.items()},
        "documents": documents,
        "stats": _four_stats_couverture(entries, len(ref)),
        # Le certificat qui porte la date d'expiration FSC. Quand il existe,
        # le champ date des Paramètres passe en lecture seule : c'est lui la
        # source, la colonne n'en est que le reflet.
        "fiche_fsc_id": fiche_fsc,
        "fsc_doc": _four_fsc_doc(entries, fiche_fsc),
    }


@router.get("/api/fournisseurs/groupe/{groupe}/fiche")
def fournisseur_groupe_fiche(groupe: str, request: Request):
    """Fiche consolidée d'un groupe : branches, agrégats et documents groupe.

    Le groupe n'est pas une ligne en base — c'est la colonne `groupe` de
    fournisseurs_fsc. Cette route l'expose comme une entité pour que la fiche
    groupe existe côté UI sans migration.
    """
    require_settings(request)
    from database import get_db
    import json
    g = (groupe or "").strip()
    if not g:
        raise HTTPException(status_code=400, detail="Groupe requis")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, nom, groupe, branche, licence, certificat, has_fsc,
                      fsc_date_expiration, categories, ville, pays, actif,
                      traca_exemple_code, traca_photo_url, traca_explication,
                      (SELECT COUNT(*) FROM fournisseur_contacts fc
                       WHERE fc.fournisseur_id = fournisseurs_fsc.id AND fc.actif=1) AS nb_contacts
               FROM fournisseurs_fsc
               WHERE LOWER(TRIM(groupe)) = LOWER(?)
               ORDER BY COALESCE(NULLIF(TRIM(branche),''), nom) COLLATE NOCASE ASC""",
            (g,),
        ).fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="Groupe non trouvé")
        ref = _four_load_referentiel(conn)
        couv, meta = _four_load_couverture(conn)
        try:
            liens = conn.execute(
                """SELECT l.certificat_id, l.fiche_id, f.nom, f.acronyme
                   FROM qualite_fournisseur_certificat_fiches l
                   JOIN qualite_ref_fiches f ON f.id = l.fiche_id"""
            ).fetchall()
        except Exception:
            liens = []
        # Réceptions : même source que GET /{id}/receptions — stock_receptions,
        # rapproché par NOM de fournisseur (pas par id : la table n'a pas de FK).
        nb_rec = {}
        for r in rows:
            try:
                nb_rec[r["id"]] = conn.execute(
                    "SELECT COUNT(*) AS n FROM stock_receptions WHERE fournisseur = ?",
                    (r["nom"],),
                ).fetchone()["n"]
            except Exception:
                nb_rec[r["id"]] = 0

    fiches_par_cert = {}
    for lk in liens:
        fiches_par_cert.setdefault(lk["certificat_id"], []).append(
            {"fiche_id": lk["fiche_id"], "nom": lk["nom"], "acronyme": lk["acronyme"]}
        )

    branches = []
    union = {}
    for r in rows:
        d = dict(r)
        try:
            d["categories"] = json.loads(d["categories"]) if d.get("categories") else []
        except (json.JSONDecodeError, TypeError):
            d["categories"] = []
        entries = couv.get(r["id"], {})
        d["couverture"] = {str(k): v for k, v in entries.items()}
        d["stats"] = _four_stats_couverture(entries, len(ref))
        d["nb_receptions"] = nb_rec.get(r["id"], 0)
        branches.append(d)
        for k, v in entries.items():
            cur = union.get(k)
            if cur is None or _FOUR_CERT_RANG.get(v["statut"], 9) < _FOUR_CERT_RANG.get(cur["statut"], 9):
                union[k] = v

    gl = g.lower()
    documents_groupe = []
    for cid, m in meta.items():
        if (m.get("groupe_ref") or "").strip().lower() != gl:
            continue
        documents_groupe.append({
            "id": cid,
            "titre": m.get("titre") or m.get("original_name") or "",
            "filename": m.get("original_name") or "",
            "date_emission": m.get("date_emission"),
            "date_expiration": m.get("date_expiration"),
            "statut": _four_cert_statut(m.get("date_expiration")),
            "fiches": fiches_par_cert.get(cid, []),
        })
    documents_groupe.sort(key=lambda d: d["titre"].lower())

    return {
        "groupe": rows[0]["groupe"],
        "branches": branches,
        "referentiel": ref,
        "documents_groupe": documents_groupe,
        "union": {str(k): v for k, v in union.items()},
        "stats": {
            "nb_branches": len(branches),
            "nb_actives": sum(1 for b in branches if (b.get("actif") is None or b["actif"])),
            "nb_receptions": sum(b["nb_receptions"] for b in branches),
            "nb_contacts": sum(int(b.get("nb_contacts") or 0) for b in branches),
            "couvert": len(union),
            "total": len(ref),
        },
    }


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


# ── Champs FSC du fournisseur ────────────────────────────────────────
# `sous_traitant` et `categories` disent la même chose sous deux formes : la
# migration 213 a introduit `categories` (liste JSON) en gardant la colonne
# booléenne pour la rétrocompatibilité. On les tient synchronisées ici, dans
# UN seul endroit — deux sources de vérité qui divergent, c'est exactement
# comment la case a fini par ne plus rien vouloir dire.
# Le référentiel des catégories vit dans config.py (FOURNISSEUR_CATEGORIES),
# lu ici comme côté client via GET /api/fournisseurs/categories. Il y avait
# jusqu'ici deux vocabulaires concurrents — une constante morte côté serveur
# et une liste codée en dur dans settings_page.py — et aucun endpoint pour les
# départager : le front tombait systématiquement sur son repli. Conséquence :
# tout code stocké hors de ce repli restait affiché en brut et impossible à
# décocher (le picker le conservait dans sa sélection), ce qui se lit très
# exactement comme « changer la catégorie ne prend pas ».


def _parse_fournisseur_categories(raw):
    """Normalise la liste de catégories. Renvoie (liste, json, sous_traitant).

    Les codes inconnus du référentiel sont écartés : conserver un code
    qu'aucune interface ne sait ni nommer ni décocher revient à le rendre
    définitif.
    """
    import json as _json
    from config import FOURNISSEUR_CATEGORIES_CODES
    cats = []
    if isinstance(raw, list):
        cats = [str(c).strip() for c in raw if str(c).strip()]
    elif isinstance(raw, str) and raw.strip():
        try:
            parsed = _json.loads(raw)
            if isinstance(parsed, list):
                cats = [str(c).strip() for c in parsed if str(c).strip()]
        except (ValueError, TypeError):
            cats = [c.strip() for c in raw.split(",") if c.strip()]
    # Doublons retirés, ordre d'apparition conservé (lisibilité côté UI).
    vus, propres = set(), []
    for c in cats:
        if c in vus or c not in FOURNISSEUR_CATEGORIES_CODES:
            continue
        vus.add(c)
        propres.append(c)
    return propres, (_json.dumps(propres, ensure_ascii=False) if propres else None), \
        (1 if "sous_traitant" in propres else 0)


def _parse_fsc_date_expiration(raw):
    """Date d'expiration du certificat FSC — format ISO AAAA-MM-JJ.

    Refusée si mal formée plutôt que stockée telle quelle : une date que le
    contrôle de validité ne saura pas lire équivaut à une absence de contrôle,
    en donnant l'illusion inverse.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Date d'expiration du certificat FSC invalide (attendu AAAA-MM-JJ).",
        )
    return s


# ═══════════════════════════════════════════════════════════════════════
# Coordonnées société, conditions d'achat et fiscalité
#
# Ces champs décrivent l'ENTREPRISE, pas une personne : le standard et
# l'adresse générique de commande survivent au contact qui y répond.
# `fournisseur_contacts` garde les personnes.
#
# Chaque valeur est refusée si elle est mal formée, plutôt que stockée telle
# quelle. Un SIRET à 12 chiffres ou un régime de TVA inconnu ne provoque
# aucune erreur visible tant qu'on ne s'en sert pas — et le jour où l'on
# s'en sert, c'est une écriture comptable fausse ou un index qui ne
# rapproche rien.
# ═══════════════════════════════════════════════════════════════════════

_FOUR_COLS_ACHAT = (
    "siret", "tva_intracom", "rcs",
    "telephone", "email", "fax",
    "mode_reglement", "mode_livraison", "delai_expedition_jours",
    "regime_tva",
)


def _txt_ou_none(v, maxlen=0):
    if v is None:
        return None
    s = " ".join(str(v).split())
    if not s:
        return None
    return s[:maxlen] if maxlen and len(s) > maxlen else s


def _parse_siret(raw):
    s = _txt_ou_none(raw)
    if not s:
        return None
    chiffres = re.sub(r"\D", "", s)
    if len(chiffres) not in (9, 14):
        raise HTTPException(
            status_code=400,
            detail="SIRET invalide — 14 chiffres attendus (ou 9 pour un SIREN).",
        )
    return chiffres


def _parse_tva_intracom(raw):
    s = _txt_ou_none(raw)
    if not s:
        return None
    s = re.sub(r"[^A-Za-z0-9]", "", s).upper()
    if not re.match(r"^[A-Z]{2}[0-9A-Z]{6,13}$", s):
        raise HTTPException(
            status_code=400,
            detail="Numéro de TVA invalide — deux lettres de pays puis 6 à 13 caractères (ex. FR81511760092).",
        )
    return s


def _parse_email_fournisseur(raw):
    s = _txt_ou_none(raw, 190)
    if not s:
        return None
    s = s.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", s):
        raise HTTPException(status_code=400, detail="Adresse e-mail invalide.")
    return s


def _parse_delai_expedition(raw):
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    try:
        n = int(float(str(raw).replace(",", ".")))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Délai d'expédition invalide — nombre entier de jours entre 0 et 365.",
        )
    if not 0 <= n <= 365:
        raise HTTPException(
            status_code=400,
            detail="Délai d'expédition invalide — nombre entier de jours entre 0 et 365.",
        )
    return n


def _parse_code_referentiel(raw, codes, quoi):
    """Code d'un petit référentiel de config.py, ou 400.

    Refuser plutôt qu'écarter silencieusement : un code hors référentiel ne
    peut être ni affiché lisiblement, ni décoché — c'est la leçon des
    catégories fournisseurs.
    """
    s = _txt_ou_none(raw)
    if not s:
        return None
    if s not in codes:
        raise HTTPException(
            status_code=400,
            detail=f"{quoi} inconnu : « {s} ». Valeurs acceptées : {', '.join(sorted(codes))}.",
        )
    return s


def _parse_devise_achat(raw, defaut="EUR"):
    s = _txt_ou_none(raw)
    if not s:
        return defaut
    s = s.strip().upper()
    if not re.match(r"^[A-Z]{3}$", s):
        raise HTTPException(
            status_code=400,
            detail="Devise invalide — code ISO à 3 lettres attendu (EUR, USD, GBP…).",
        )
    return s


def _champs_achat(body, ex=None, ex_cols=()):
    """Valeurs des champs coordonnées / conditions / fiscalité.

    `ex` fourni → sémantique d'édition partielle : un champ absent du body
    garde sa valeur en base. La fiche v2 enregistre bloc par bloc ; sans ce
    garde-fou, sauvegarder l'onglet Contacts effacerait le régime de TVA.
    """
    from config import (
        MODES_REGLEMENT_CODES, MODES_LIVRAISON_CODES, REGIMES_TVA_CODES,
    )

    def brut(champ, defaut=None):
        if champ in body:
            return body.get(champ)
        if ex is not None and champ in ex_cols:
            return ex[champ]
        return defaut

    return {
        "siret": _parse_siret(brut("siret")),
        "tva_intracom": _parse_tva_intracom(brut("tva_intracom")),
        "rcs": _txt_ou_none(brut("rcs"), 60),
        "telephone": _txt_ou_none(brut("telephone"), 40),
        "email": _parse_email_fournisseur(brut("email")),
        "fax": _txt_ou_none(brut("fax"), 40),
        "mode_reglement": _parse_code_referentiel(
            brut("mode_reglement"), MODES_REGLEMENT_CODES, "Mode de règlement"),
        "mode_livraison": _parse_code_referentiel(
            brut("mode_livraison"), MODES_LIVRAISON_CODES, "Mode de livraison"),
        "delai_expedition_jours": _parse_delai_expedition(brut("delai_expedition_jours")),
        "regime_tva": _parse_code_referentiel(
            brut("regime_tva"), REGIMES_TVA_CODES, "Régime de TVA"),
        "price_currency": _parse_devise_achat(
            brut("price_currency", "EUR" if ex is None else None),
            (ex["price_currency"] if (ex is not None and "price_currency" in ex_cols) else "EUR") or "EUR",
        ),
    }


# ═══════════════════════════════════════════════════════════════════════
# Doublons et fusion
#
# Ces deux endpoints étaient appelés par la page Paramètres depuis le début
# et n'existaient pas côté serveur : le bouton « Doublons » et la fusion
# renvoyaient un 404 silencieux. Un import de 199 lignes d'export ERP en
# fait le besoin immédiat — c'est exactement le moment où l'annuaire se
# retrouve avec « 2DM » à côté de « 2 D M S.A.S. ».
# ═══════════════════════════════════════════════════════════════════════

_FOUR_FORMES_JURIDIQUES = (
    "sa", "sas", "sarl", "sasu", "gmbh", "ltd", "bv", "nv", "spa", "srl",
    "inc", "snc", "eurl", "scop", "scp", "gie", "ag", "plc",
)


def _four_norm_nom(s):
    """Nom normalisé pour comparaison — même logique que la migration
    `mc_fournisseurs_annuaire_entreprise` et que le script d'import.

    Les trois doivent se tromper de la même façon : sinon l'import crée un
    doublon que la détection ne voit pas, ou l'inverse.
    """
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = "".join(ch if ch.isalnum() else " " for ch in s)
    mots = [m for m in s.split()
            if m not in _FOUR_FORMES_JURIDIQUES and len(m) > 1]
    return " ".join(mots) or " ".join(s.split())


def _four_squash(s):
    """Nom réduit aux seuls alphanumériques, suffixe juridique retiré.

    Rattrape ce que `_four_norm_nom` laisse passer : « 2 D M S.A.S. » perd
    ses initiales isolées à la normalisation et ne ressemble plus à « 2DM ».
    Utilisé pour SIGNALER une ressemblance, jamais pour fusionner d'office.
    """
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    for forme in sorted(_FOUR_FORMES_JURIDIQUES, key=len, reverse=True):
        if s.endswith(forme) and len(s) > len(forme) + 2:
            return s[: -len(forme)]
    return s


# Mots qui ne distinguent rien : les retenir ferait grouper « ETIQUETTES
# CEVENNES » avec « ETIQUETTES PIERRE FOUCHER » au seul motif qu'ils vendent
# tous deux des étiquettes.
_four_jetons_generiques = frozenset("""
de du des la le les et sas sa sarl sasu snc gie group groupe holding
france europe european international industrie industries industrial
etiquette etiquettes label labels packaging package pack paper papier papel
materials material adhesive adhesif imprimerie imprimeur print printing
company societe ste co ltd gmbh srl spa nv bv oy ab as inc corp
""".split())


def _four_jetons(nom):
    """Jetons distinctifs d'un nom, dans l'ordre."""
    return [j for j in _four_norm_nom(nom).split() if j]


def _four_jeton_proche(a, b):
    """Deux jetons désignent-ils le même mot ?

    Tolérance volontairement étroite : « torrespapel » et « torraspapel »
    (une voyelle), « foucher » et « foucherf » (une lettre en trop dans la
    fiche historique). Au-delà, ce sont deux mots différents.
    """
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1 or min(len(a), len(b)) < 5:
        return False
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio() >= 0.9


def _four_inclus(petit, grand):
    """Le nom `petit` apparaît-il comme suite de jetons dans `grand` ?

    C'est le cas que la comparaison de chaînes ratait : les fiches historiques
    portent un nom d'usage court (« Feys », « Likexin », « Shine ») et l'export
    comptable la raison sociale complète (« IMPRIMERIE FEYS », « SHENZHEN
    LIKEXIN INDUSTRIAL Co. », « GUANGZHOU SHINE LABEL MATERIALS »). Comparées
    entières, ces paires tombent sous le seuil de similarité ; comparées jeton
    par jeton, elles sautent aux yeux.

    Pourquoi c'est important : la fiche courte porte la LICENCE FSC, la longue
    l'adresse et le SIRET. Les deux coexistent dans la liste de réception, une
    seule affiche le badge FSC, et rien n'empêche d'attraper l'autre.
    """
    jp, jg = _four_jetons(petit), _four_jetons(grand)
    if not jp or not jg or len(jp) > len(jg):
        return False
    # Un seul jeton distinctif : il doit être assez long et non générique,
    # sinon « ABI » se collerait à « ABIX ».
    if len(jp) == 1:
        if jp[0] in _four_jetons_generiques or len(jp[0]) < 4:
            return False
        return any(_four_jeton_proche(jp[0], j) for j in jg)
    for depart in range(len(jg) - len(jp) + 1):
        if all(_four_jeton_proche(jp[i], jg[depart + i]) for i in range(len(jp))):
            if any(j not in _four_jetons_generiques for j in jp):
                return True
    return False


@router.get("/api/fournisseurs/doublons")
def fournisseurs_doublons(request: Request):
    """Groupes de fiches qui désignent probablement le même fournisseur.

    Quatre clés, de la plus sûre à la plus lâche : SIRET, numéro de TVA,
    nom normalisé, nom tassé. Une fiche n'apparaît que dans le premier
    groupe qui la retient — sinon « 2DM » et « 2 D M S.A.S. » se lisent
    quatre fois et le rapport devient illisible.
    """
    require_settings(request)
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT ff.id, ff.nom, ff.siret, ff.tva_intracom, ff.ville,
                      ff.has_fsc, ff.actif, ff.groupe,
                      (SELECT COUNT(*) FROM fournisseur_contacts fc
                        WHERE fc.fournisseur_id = ff.id AND fc.actif = 1) AS nb_contacts
                 FROM fournisseurs_fsc ff
                ORDER BY ff.nom COLLATE NOCASE ASC"""
        ).fetchall()

    fiches = [dict(r) for r in rows]
    groups = []
    deja = set()

    def _ajouter(cle_fn, reason, libelle_fn=None):
        paniers = {}
        for f in fiches:
            if f["id"] in deja:
                continue
            k = cle_fn(f)
            if not k:
                continue
            paniers.setdefault(k, []).append(f)
        for k, membres in paniers.items():
            if len(membres) < 2:
                continue
            for m in membres:
                deja.add(m["id"])
            groups.append({
                "reason": reason,
                "key": (libelle_fn(k, membres) if libelle_fn else k),
                "count": len(membres),
                "fournisseurs": [
                    {"id": m["id"], "nom": m["nom"], "siret": m["siret"],
                     "ville": m["ville"], "has_fsc": 1 if m["has_fsc"] else 0,
                     "actif": 1 if (m["actif"] is None or m["actif"]) else 0,
                     "nb_contacts": m["nb_contacts"]}
                    for m in membres
                ],
            })

    _ajouter(lambda f: re.sub(r"\D", "", str(f["siret"] or "")) or None, "siret")
    _ajouter(lambda f: re.sub(r"[^A-Z0-9]", "", str(f["tva_intracom"] or "").upper()) or None,
             "tva")
    _ajouter(lambda f: _four_norm_nom(f["nom"]) or None, "nom",
             lambda k, membres: membres[0]["nom"])
    _ajouter(lambda f: _four_squash(f["nom"]) or None, "nom",
             lambda k, membres: membres[0]["nom"])

    # Passe « inclusion » : plus coûteuse (comparaison de paires), donc en
    # dernier, sur ce que les clés exactes n'ont pas déjà groupé. À l'échelle
    # d'un annuaire fournisseurs — quelques centaines de fiches — le coût est
    # sans conséquence, et cette passe est la seule qui rapproche un nom
    # d'usage de sa raison sociale.
    restants = [f for f in fiches if f["id"] not in deja]
    # Le nom le plus court d'abord : c'est lui qu'on cherche DANS les autres.
    restants.sort(key=lambda f: len(_four_norm_nom(f["nom"])))
    for i, court in enumerate(restants):
        if court["id"] in deja:
            continue
        groupe = [court]
        for long in restants[i + 1:]:
            if long["id"] in deja:
                continue
            if _four_inclus(court["nom"], long["nom"]):
                groupe.append(long)
        if len(groupe) < 2:
            continue
        for m in groupe:
            deja.add(m["id"])
        groups.append({
            "reason": "nom",
            "key": court["nom"],
            "count": len(groupe),
            "fournisseurs": [
                {"id": m["id"], "nom": m["nom"], "siret": m["siret"],
                 "ville": m["ville"], "has_fsc": 1 if m["has_fsc"] else 0,
                 "actif": 1 if (m["actif"] is None or m["actif"]) else 0,
                 "nb_contacts": m["nb_contacts"]}
                for m in groupe
            ],
        })

    # SIRET d'abord : c'est la seule clé qu'on n'invente pas. Le nom passe en
    # dernier, il produit le plus de faux positifs.
    ordre = {"siret": 0, "tva": 1, "nom": 2}
    groups.sort(key=lambda g: (ordre.get(g["reason"], 9), -g["count"]))
    return {"groups": groups, "total_fiches": len(fiches)}


def _four_refs_fournisseur(conn):
    """Introspecte le schéma : où l'id d'un fournisseur est-il référencé ?

    Volontairement générique. Une quinzaine de tables portent aujourd'hui un
    `fournisseur_id` et le nombre grandit à chaque chantier ; une liste écrite
    à la main serait périmée au prochain merge, et une fusion qui oublie une
    table laisse des lignes pointant vers un id supprimé — donc des écrans
    vides sans message d'erreur.

    Renvoie (refs_id, refs_nom, refs_json) :
      refs_id   [(table, colonne, cles_unicite)]  colonnes d'id
      refs_nom  [(table, colonne)]                colonnes portant le NOM
      refs_json [(table, colonne)]                listes d'ids en JSON
    """
    refs_id, refs_nom, refs_json = [], [], []
    tables = [
        r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    ]
    for t in tables:
        if t == "fournisseurs_fsc":
            continue
        try:
            cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
        except Exception:
            continue
        noms = [c["name"] for c in cols]
        pk = [c["name"] for c in cols if c["pk"]]
        uniques = set(pk)
        try:
            for idx in conn.execute(f"PRAGMA index_list({t})").fetchall():
                if not idx["unique"]:
                    continue
                for ic in conn.execute(f"PRAGMA index_info({idx['name']})").fetchall():
                    if ic["name"]:
                        uniques.add(ic["name"])
        except Exception:
            pass
        for c in noms:
            if c in ("fournisseur_id", "fournisseur_fsc_id", "source_fournisseur_id"):
                refs_id.append((t, c, uniques))
            elif c == "fournisseur":
                refs_nom.append((t, c))
            elif "fournisseur" in c and (c.endswith("_json") or c.endswith("_ids")):
                refs_json.append((t, c))
    return refs_id, refs_nom, refs_json


@router.post("/api/fournisseurs/{source_id}/merge/{target_id}")
def merge_fournisseurs(source_id: int, target_id: int, request: Request):
    """Réassigne tout ce qui pend à `source_id` vers `target_id`, puis
    supprime la source.

    Irréversible, d'où le double garde-fou côté interface (case à cocher +
    confirmation). Côté serveur, tout tient dans UNE transaction : une fusion
    à moitié faite laisserait des contacts orphelins et un fournisseur
    fantôme, état dont on ne sort pas sans SQL à la main.
    """
    user = require_settings(request)
    if source_id == target_id:
        raise HTTPException(status_code=400,
                            detail="Source et cible identiques — rien à fusionner.")
    from database import get_db
    import json as _json

    with get_db() as conn:
        src = conn.execute("SELECT * FROM fournisseurs_fsc WHERE id=?", (source_id,)).fetchone()
        tgt = conn.execute("SELECT * FROM fournisseurs_fsc WHERE id=?", (target_id,)).fetchone()
        if not src:
            raise HTTPException(status_code=404, detail="Fournisseur source non trouvé")
        if not tgt:
            raise HTTPException(status_code=404, detail="Fournisseur cible non trouvé")

        refs_id, refs_nom, refs_json = _four_refs_fournisseur(conn)
        moved, renamed = {}, {}
        json_rewrites = 0

        try:
            conn.execute("BEGIN")

            for table, col, uniques in refs_id:
                # UPDATE OR IGNORE : quand la table impose l'unicité du couple
                # (fournisseur, autre chose) — mc_tarif_fournisseur,
                # matiere_laize_fournisseurs — la cible peut déjà porter la
                # ligne équivalente. On la garde, elle : c'est la fiche qui
                # survit, ses réglages sont ceux que l'utilisateur voit.
                if col in uniques or (uniques & {col}):
                    cur = conn.execute(
                        f"UPDATE OR IGNORE {table} SET {col}=? WHERE {col}=?",
                        (target_id, source_id))
                    deplacees = cur.rowcount
                    reste = conn.execute(
                        f"DELETE FROM {table} WHERE {col}=?", (source_id,)).rowcount
                    if deplacees or reste:
                        moved[table] = deplacees
                        if reste:
                            moved[f"{table} (doublons écartés)"] = reste
                else:
                    cur = conn.execute(
                        f"UPDATE {table} SET {col}=? WHERE {col}=?",
                        (target_id, source_id))
                    if cur.rowcount:
                        moved[table] = cur.rowcount

            for table, col in refs_nom:
                # Historique stocké par NOM (stock_receptions.fournisseur,
                # matiere_params.fournisseur). On renomme : effacer couperait
                # la traçabilité d'une réception déjà partie en production.
                cur = conn.execute(
                    f"UPDATE {table} SET {col}=? WHERE {col}=?", (tgt["nom"], src["nom"]))
                if cur.rowcount:
                    renamed[table] = cur.rowcount

            for table, col in refs_json:
                lignes = conn.execute(
                    f"SELECT rowid AS rid, {col} AS v FROM {table} "
                    f"WHERE {col} IS NOT NULL AND {col} LIKE ?",
                    (f"%{source_id}%",)).fetchall()
                for l in lignes:
                    try:
                        val = _json.loads(l["v"])
                    except (ValueError, TypeError):
                        continue
                    if not isinstance(val, list):
                        continue
                    neuf, change = [], False
                    for x in val:
                        y = target_id if (isinstance(x, int) and x == source_id) else x
                        if y != x:
                            change = True
                        if y not in neuf:
                            neuf.append(y)
                    if change:
                        conn.execute(
                            f"UPDATE {table} SET {col}=? WHERE rowid=?",
                            (_json.dumps(neuf), l["rid"]))
                        json_rewrites += 1

            # Ce que la cible n'a pas et que la source portait : on le récupère
            # plutôt que de le perdre avec la fiche. Les champs déjà remplis sur
            # la cible ne bougent pas — c'est elle qui survit.
            recuperables = [
                "licence", "certificat", "groupe", "branche", "adresse",
                "code_postal", "ville", "siret", "tva_intracom", "rcs",
                "telephone", "email", "fax", "mode_reglement", "mode_livraison",
                "delai_expedition_jours", "regime_tva", "notes",
                "traca_photo_url", "traca_explication", "traca_exemple_code",
                "fsc_date_expiration",
            ]
            tgt_cols = tgt.keys()
            sets, vals, recup = [], [], []
            for champ in recuperables:
                if champ not in tgt_cols:
                    continue
                a, b = tgt[champ], src[champ]
                if (a is None or str(a).strip() == "") and b not in (None, ""):
                    sets.append(f"{champ}=?")
                    vals.append(b)
                    recup.append(champ)
            # Catégories : union. Deux fiches du même fournisseur peuvent avoir
            # été rangées différemment, les deux rangements sont justes.
            if "categories" in tgt_cols:
                def _liste(v):
                    try:
                        p = _json.loads(v) if v else []
                        return p if isinstance(p, list) else []
                    except (ValueError, TypeError):
                        return []
                union = _liste(tgt["categories"])
                for c in _liste(src["categories"]):
                    if c not in union:
                        union.append(c)
                if union != _liste(tgt["categories"]):
                    sets.append("categories=?")
                    vals.append(_json.dumps(union, ensure_ascii=False))
                    recup.append("categories")
                    if "sous_traitant" in tgt_cols and "sous_traitant" in union:
                        sets.append("sous_traitant=?")
                        vals.append(1)
            if "has_fsc" in tgt_cols and not tgt["has_fsc"] and src["has_fsc"]:
                sets.append("has_fsc=?")
                vals.append(1)
                recup.append("has_fsc")
            if sets:
                sets.append("updated_at=?")
                vals.append(datetime.now().isoformat())
                vals.append(target_id)
                conn.execute(
                    f"UPDATE fournisseurs_fsc SET {', '.join(sets)} WHERE id=?", vals)

            conn.execute("DELETE FROM fournisseurs_fsc WHERE id=?", (source_id,))
            conn.commit()
        except HTTPException:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Fusion interrompue et annulée — aucune donnée modifiée. ({e})",
            )

    log_action(
        user=user,
        action="DELETE",
        module="settings",
        objet=f"Fusion fournisseur {src['nom']} → {tgt['nom']}",
        detail={"source_id": source_id, "target_id": target_id,
                "moved": moved, "renamed": renamed,
                "json_rewrites": json_rewrites,
                "champs_recuperes": recup},
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "moved": moved, "renamed": renamed,
            "json_rewrites": json_rewrites, "champs_recuperes": recup,
            "target": {"id": target_id, "nom": tgt["nom"]}}


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
    cat_list, cat_json, sous_traitant = _parse_fournisseur_categories(body.get("categories"))
    fsc_date_expiration = _parse_fsc_date_expiration(body.get("fsc_date_expiration"))
    if not has_fsc:
        fsc_date_expiration = None
    achat = _champs_achat(body)
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du fournisseur requis")
    now = datetime.now().isoformat()
    with get_db() as conn:
        try:
            cur = conn.execute(
                """INSERT INTO fournisseurs_fsc
                   (nom, licence, certificat, has_fsc, groupe, branche,
                    adresse, code_postal, ville, pays, langue_default, tags,
                    notes, actif, updated_at,
                    fsc_date_expiration, sous_traitant, categories,
                    siret, tva_intracom, rcs, telephone, email, fax,
                    mode_reglement, mode_livraison, delai_expedition_jours,
                    regime_tva, price_currency)
                   VALUES (?,?,?,?,?,?, ?,?,?,?,?,?, ?,?,?, ?,?,?,
                           ?,?,?,?,?,?, ?,?,?, ?,?)""",
                (nom, licence, certificat, has_fsc, groupe, branche,
                 adresse, code_postal, ville, pays, langue_default, tags_json,
                 notes, actif, now,
                 fsc_date_expiration, sous_traitant, cat_json,
                 achat["siret"], achat["tva_intracom"], achat["rcs"],
                 achat["telephone"], achat["email"], achat["fax"],
                 achat["mode_reglement"], achat["mode_livraison"],
                 achat["delai_expedition_jours"],
                 achat["regime_tva"], achat["price_currency"]),
            )
            conn.commit()
            log_action(
                user=user,
                action="CREATE",
                module="settings",
                objet=f"Fournisseur {nom}",
                detail={"has_fsc": bool(has_fsc), "langue_default": langue_default,
                        "tags": tags_list, "ville": ville, "pays": pays,
                        "actif": bool(actif), "categories": cat_list,
                        "sous_traitant": bool(sous_traitant),
                        "fsc_date_expiration": fsc_date_expiration},
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

        # RVGI prime. Sur une fiche liée, les champs que l'ERP pilote sont
        # verrouillés dans l'interface — mais l'interface n'est pas une
        # sécurité : un ancien onglet, un script, un rejeu de formulaire les
        # renverraient quand même. On les retire du corps reçu, et `_pick`
        # reprend alors la valeur en base. Le refus est silencieux parce qu'il
        # n'y a rien à refuser : la valeur envoyée était déjà la bonne, ou
        # elle n'aurait pas dû partir.
        if ("rvgi_etat" in ex_cols) and ex["rvgi_etat"] == "lie":
            try:
                from app.services.rvgi_tiers import champs_pilotes
                for _c in champs_pilotes("fournisseur"):
                    body.pop(_c, None)
            except Exception:
                pass
        # Le lien lui-même ne se change pas par cette route : /api/rvgi-tiers/lier
        # est le seul endroit qui le pose, et il contrôle l'unicité.
        for _c in ("rvgi_numero", "rvgi_code", "rvgi_etat", "rvgi_motif",
                   "rvgi_score", "rvgi_bloq", "rvgi_rs", "rvgi_groupe",
                   "rvgi_lie_le", "rvgi_maj_le"):
            body.pop(_c, None)

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
        # Traçabilité : même garde-fou que les autres champs. Ces deux colonnes
        # étaient écrasées à NULL dès qu'un enregistrement partiel ne les
        # portait pas — la fiche v2 édite bloc par bloc, donc chaque save
        # aurait effacé le guide opérateur du fournisseur.
        traca_explication = _pick("traca_explication")
        traca_exemple_code = _pick("traca_exemple_code")
        if isinstance(traca_explication, str): traca_explication = traca_explication.strip() or None
        if isinstance(traca_exemple_code, str): traca_exemple_code = traca_exemple_code.strip() or None
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

        # Champs FSC : on ne les écrase que s'ils sont explicitement fournis.
        # Le front n'envoie pas toujours l'objet complet (édition partielle
        # depuis la fiche contact, par exemple) — sans ce garde-fou, une
        # sauvegarde partielle effacerait la date d'expiration du certificat.
        if "categories" in body:
            cat_list, cat_json, sous_traitant = _parse_fournisseur_categories(body.get("categories"))
        else:
            cat_json = ex["categories"] if "categories" in ex_cols else None
            cat_list, cat_json, sous_traitant = _parse_fournisseur_categories(cat_json)
        if "fsc_date_expiration" in body:
            fsc_date_expiration = _parse_fsc_date_expiration(body.get("fsc_date_expiration"))
        else:
            fsc_date_expiration = ex["fsc_date_expiration"] if "fsc_date_expiration" in ex_cols else None
        # Édition partielle : la fiche v2 enregistre bloc par bloc, donc un
        # champ absent du body garde sa valeur en base.
        achat = _champs_achat(body, ex, ex_cols)

        # Le certificat déposé dans MyQualité fait foi. Si ce fournisseur en a
        # un, sa date écrase ce que le body propose : sans ce garde-fou, un
        # onglet resté ouvert (ou un appel direct à l'API) pourrait réintroduire
        # la divergence que la synchro vient de corriger.
        try:
            ref_rse = _four_load_referentiel(conn)
            fiche_fsc = _four_fiche_fsc_id(ref_rse)
            if fiche_fsc:
                couv_all, _m = _four_load_couverture(conn)
                doc_fsc = _four_fsc_doc(couv_all.get(fournisseur_id), fiche_fsc)
                if doc_fsc and doc_fsc.get("date_expiration"):
                    fsc_date_expiration = str(doc_fsc["date_expiration"])[:10]
        except Exception:
            pass  # MyQualité absent : on garde la saisie manuelle
        # Un fournisseur non certifié ne peut pas porter de date d'expiration
        # de certificat : la garder laisserait une donnée orpheline que le
        # contrôle de validité interpréterait de travers.
        if not has_fsc:
            fsc_date_expiration = None

        now = datetime.now().isoformat()

        changed = {}
        _pairs = [
            ("nom", ex["nom"], nom),
            ("has_fsc", has_fsc_prev, has_fsc),
            ("langue_default", (ex["langue_default"] if "langue_default" in ex_cols else None), langue_default),
            ("ville", (ex["ville"] if "ville" in ex_cols else None), ville),
            ("actif", actif_prev, actif),
            ("sous_traitant",
             (int(ex["sous_traitant"] or 0) if "sous_traitant" in ex_cols else 0),
             sous_traitant),
            ("fsc_date_expiration",
             (ex["fsc_date_expiration"] if "fsc_date_expiration" in ex_cols else None),
             fsc_date_expiration),
        ]
        # Identité fiscale et conditions d'achat : ce sont les champs qui
        # engagent (SIRET faux = facture non déductible, régime de TVA faux =
        # écriture comptable fausse). Ils appartiennent au journal d'audit.
        for _c in _FOUR_COLS_ACHAT + ("price_currency",):
            if _c in ex_cols:
                _pairs.append((_c, ex[_c], achat.get(_c)))
        for name, before, after in _pairs:
            if before != after:
                changed[name] = {"before": before, "after": after}

        try:
            conn.execute(
                """UPDATE fournisseurs_fsc SET
                       nom=?, licence=?, certificat=?, has_fsc=?,
                       traca_explication=?, traca_exemple_code=?, groupe=?, branche=?,
                       adresse=?, code_postal=?, ville=?, pays=?,
                       langue_default=?, tags=?, notes=?, actif=?, updated_at=?,
                       fsc_date_expiration=?, sous_traitant=?, categories=?,
                       siret=?, tva_intracom=?, rcs=?,
                       telephone=?, email=?, fax=?,
                       mode_reglement=?, mode_livraison=?, delai_expedition_jours=?,
                       regime_tva=?, price_currency=?
                   WHERE id=?""",
                (nom, licence, certificat, has_fsc,
                 traca_explication, traca_exemple_code, groupe, branche,
                 adresse, code_postal, ville, pays,
                 langue_default, tags_json, notes, actif, now,
                 fsc_date_expiration, sous_traitant, cat_json,
                 achat["siret"], achat["tva_intracom"], achat["rcs"],
                 achat["telephone"], achat["email"], achat["fax"],
                 achat["mode_reglement"], achat["mode_livraison"],
                 achat["delai_expedition_jours"],
                 achat["regime_tva"], achat["price_currency"],
                 fournisseur_id),
            )
            conn.commit()
            log_action(
                user=user,
                action="UPDATE",
                module="settings",
                objet=f"Fournisseur {nom}",
                detail={"changed": changed, "tags": tags_list, "categories": cat_list},
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
        # Jointure par id ET par nom. `stock_receptions.fournisseur_id` existe
        # depuis la migration `fsc_reception_fournisseur_id`, mais les
        # réceptions antérieures ne portent que le nom en texte : ne joindre
        # que sur l'id viderait l'historique, ne joindre que sur le nom le
        # perdrait au premier renommage. Les deux, le temps que les anciennes
        # lignes finissent de vivre.
        a_col_id = any(
            r[1] == "fournisseur_id"
            for r in conn.execute("PRAGMA table_info(stock_receptions)").fetchall()
        )
        clause = ("(r.fournisseur_id = ? OR (r.fournisseur_id IS NULL AND r.fournisseur = ?))"
                  if a_col_id else "r.fournisseur = ?")
        params = (fournisseur_id, four["nom"]) if a_col_id else (four["nom"],)
        rows = conn.execute(
            f"""SELECT r.id, r.created_at, r.created_by_name, r.nb_bobines,
                      r.certificat_fsc, r.note,
                      GROUP_CONCAT(i.code_barre, '||') as codes
               FROM stock_receptions r
               LEFT JOIN stock_reception_items i ON i.reception_id = r.id
               WHERE {clause}
               GROUP BY r.id
               ORDER BY r.created_at DESC LIMIT 50""",
            params,
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
import datetime as _dt
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


# ─── Santé du dépôt et du schéma ───────────────────────────────────────────────
# Vue de CONSULTATION uniquement : aucune commande git qui écrit, aucune action
# destructive. Elle sert à vérifier avant de promouvoir que le schéma est à jour,
# qu'aucune branche morte ne traîne et que le dossier de travail est propre.


def _git_lire(*args: str, defaut: str = "") -> str:
    """Commande git en LECTURE seule. Jamais d'écriture depuis l'interface."""
    try:
        return _subprocess.check_output(
            [_GIT_BIN, "-C", V2_REPO_PATH, *args],
            text=True, timeout=15, stderr=_subprocess.DEVNULL,
        ).strip()
    except Exception:
        return defaut


def _jours_depuis(iso: str) -> Optional[int]:
    try:
        d = _dt.datetime.strptime(iso[:10], "%Y-%m-%d")
        return (_dt.datetime.now() - d).days
    except Exception:
        return None


def _migrations_etat() -> dict:
    """
    Migrations appliquées sur CETTE instance, et celles présentes dans le code
    mais pas encore jouées. Signale aussi les numéros historiques en double :
    une migration qui partage son numéro avec une autre ne s'exécute jamais.
    """
    from database import get_db

    appliquees: list[dict] = []
    doublons: list[dict] = []
    noms_faits: set[str] = set()
    with get_db() as conn:
        try:
            for r in conn.execute(
                "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
            ).fetchall():
                appliquees.append({
                    "cle": str(r["version"]),
                    "nom": r["name"],
                    "date": r["applied_at"],
                    "source": "numérotée",
                })
                if r["name"]:
                    noms_faits.add(r["name"])
            vus: dict = {}
            for m in appliquees:
                vus.setdefault(m["cle"], []).append(m["nom"])
            for cle, noms in vus.items():
                if len(noms) > 1:
                    doublons.append({"cle": cle, "noms": noms})
        except Exception:
            pass
        try:
            for r in conn.execute(
                "SELECT nom, applique_le FROM schema_migrations_fichiers ORDER BY applique_le"
            ).fetchall():
                appliquees.append({
                    "cle": r["nom"], "nom": r["nom"],
                    "date": r["applique_le"], "source": "fichier",
                })
                noms_faits.add(r["nom"])
        except Exception:
            pass

    # Migrations déclarées dans le code : celles en fichiers sont lisibles sans
    # les exécuter, les historiques numérotées ne le sont pas.
    en_attente: list[dict] = []
    total_fichiers = 0
    try:
        import app.core.migrations as _mig_pkg
        import importlib
        import pkgutil

        for m in sorted(x.name for x in pkgutil.iter_modules(_mig_pkg.__path__)):
            if m.startswith("_"):
                continue
            total_fichiers += 1
            mod = importlib.import_module(f"app.core.migrations.{m}")
            nom = getattr(mod, "NOM", None)
            if nom and nom not in noms_faits:
                en_attente.append({"nom": nom, "fichier": m + ".py"})
    except Exception:
        pass

    appliquees.sort(key=lambda x: (x["date"] or ""), reverse=True)
    return {
        "appliquees": appliquees[:40],
        "nb_appliquees": len(appliquees),
        "derniere": appliquees[0] if appliquees else None,
        "en_attente": en_attente,
        "nb_fichiers": total_fichiers,
        "doublons": doublons,
    }


def _branches_etat() -> list[dict]:
    """Branches distantes, leur âge et leur état de fusion dans staging."""
    fusionnees = set()
    for ligne in _git_lire("branch", "-r", "--merged", "origin/staging").split("\n"):
        ref = ligne.strip().replace("origin/", "", 1)
        if ref and "->" not in ref:
            fusionnees.add(ref)
    sortie = _git_lire(
        "for-each-ref", "--sort=-committerdate", "refs/remotes/origin",
        "--format=%(refname:short)|%(committerdate:format:%Y-%m-%d %H:%M)|%(authorname)|%(subject)",
    )
    branches: list[dict] = []
    for ligne in sortie.split("\n"):
        if not ligne or "->" in ligne:
            continue
        parts = ligne.split("|", 3)
        if len(parts) != 4:
            continue
        nom = parts[0].replace("origin/", "", 1)
        # refs/remotes/origin/HEAD est un alias symbolique, pas une branche.
        # Selon la version de git il ressort en « origin/HEAD » ou en « origin » :
        # sans ce filtre, une ligne fantôme « origin » s'affiche dans le tableau.
        if nom in ("HEAD", "origin", "") or nom.endswith("/HEAD"):
            continue
        jours = _jours_depuis(parts[1])
        est_fusionnee = nom in fusionnees
        branches.append({
            "nom": nom,
            "date": parts[1],
            "auteur": parts[2],
            "dernier_commit": parts[3],
            "jours": jours,
            "fusionnee": est_fusionnee,
            "protegee": nom in ("main", "staging"),
            # Une branche fusionnée et sans activité depuis deux semaines n'a
            # plus de raison d'exister : c'est le signal de ménage.
            "a_nettoyer": est_fusionnee and nom not in ("main", "staging")
                          and (jours is not None and jours >= 14),
        })
    return branches


def _dossier_etat() -> dict:
    """Propreté du dossier de travail de l'instance qui répond."""
    porcelain = _git_lire("status", "--porcelain")
    modifies, non_suivis = [], []
    for ligne in porcelain.split("\n"):
        if not ligne.strip():
            continue
        code, _, chemin = ligne.partition(" ")
        (non_suivis if ligne.startswith("??") else modifies).append(chemin.strip() or ligne)
    verrou = (Path(V2_REPO_PATH) / ".git" / "index.lock").exists()
    return {
        "branche": _git_lire("rev-parse", "--abbrev-ref", "HEAD", defaut="?"),
        "nb_modifies": len(modifies),
        "nb_non_suivis": len(non_suivis),
        "modifies": modifies[:20],
        "non_suivis": non_suivis[:20],
        "verrou_git": verrou,
        "propre": not modifies and not non_suivis and not verrou,
    }


def _git_rafraichir_refs() -> bool:
    """Met à jour les références distantes du dépôt lu. Renvoie True si ça a tenu.

    Sans ça, la vue lit un miroir figé : `for-each-ref refs/remotes/origin` ne
    connaît que ce que CE dépôt a fetché la dernière fois. Une branche supprimée
    sur GitHub il y a une heure y figure encore, et le compteur « à nettoyer »
    ne redescend jamais — c'est exactement ce qui s'est passé après le premier
    grand ménage du 27 août : 46 branches supprimées, panneau toujours à 48.

    `--prune` n'est pas décoratif : un fetch nu AJOUTE les nouvelles références
    mais ne retire jamais celles dont la branche a disparu. C'est la seule
    commande qui fait redescendre le compteur.

    Ça reste sans effet sur le code : `fetch --prune` n'écrit que dans
    refs/remotes/*, jamais dans l'index, le dossier de travail ou une branche
    locale. `/api/promote/status` fait déjà le même fetch silencieux avant de
    comparer les HEAD.
    """
    try:
        r = _subprocess.run(
            [_GIT_BIN, "-C", V2_REPO_PATH, "fetch", "--prune", "--quiet"],
            check=False, capture_output=True, timeout=20,
        )
        return r.returncode == 0
    except Exception as exc:  # noqa: BLE001 — vue de consultation
        print(f"[MySifa] santé du dépôt — refs non rafraîchies : {exc}")
        return False


# ─── Note de santé du dépôt ────────────────────────────────────────────────────
# Une note sur 100 pour lire l'état du dépôt sans dérouler les trois sections.
# Elle part de 100 et retire des points par critère. Chaque critère annonce ce
# qu'il coûte ET pourquoi : une note qui baisse sans dire de quoi ne sert à rien.
#
# Les poids traduisent le risque réel, pas la gêne visuelle :
#   - un numéro de migration en double est un piège silencieux (la seconde ne
#     s'exécute jamais, et rien ne le signale) — c'est le plus lourd ;
#   - un verrou git bloque toute commande sur le dépôt ;
#   - des branches mortes ne cassent rien, mais elles noient les branches vives.

# Branches fusionnées et dormantes tolérées avant que la note ne bouge.
NOTE_TOLERANCE_BRANCHES = 5


def _note_sante(migrations: dict, branches: list, dossier: dict) -> dict:
    """Score /100, lettre et détail des points perdus. Lecture seule."""
    criteres: list[dict] = []

    def _critere(cle, label, perdu, plafond, detail):
        perdu = int(min(round(perdu), plafond))
        criteres.append({
            "cle": cle,
            "label": label,
            "perdu": perdu,
            "plafond": plafond,
            "detail": detail,
            "ok": perdu == 0,
        })

    nb_doublons = len(migrations.get("doublons") or [])
    _critere(
        "doublons", "Numéros de migration en double", nb_doublons * 15, 30,
        "Aucun doublon — chaque migration enregistrée s'est bien exécutée."
        if not nb_doublons else
        f"{nb_doublons} numéro(s) partagé(s) : la seconde migration de chaque "
        "paire n'a jamais tourné, sans le moindre message.",
    )

    nb_attente = len(migrations.get("en_attente") or [])
    _critere(
        "migrations", "Migrations en attente", nb_attente * 8, 20,
        "Schéma à jour sur cette instance."
        if not nb_attente else
        f"{nb_attente} migration(s) présente(s) dans le code et pas encore "
        "appliquée(s) ici — elles passeront au prochain démarrage.",
    )

    nb_mortes = len([b for b in branches if b.get("a_nettoyer")])
    _critere(
        "branches", "Branches fusionnées dormantes",
        max(0, nb_mortes - NOTE_TOLERANCE_BRANCHES), 25,
        "Le dépôt distant est net."
        if not nb_mortes else
        f"{nb_mortes} branche(s) fusionnée(s) dans staging et sans activité "
        f"depuis plus de deux semaines ({NOTE_TOLERANCE_BRANCHES} tolérée(s) "
        "avant pénalité).",
    )

    verrou = bool(dossier.get("verrou_git"))
    _critere(
        "verrou", "Verrou git", 20 if verrou else 0, 20,
        "Aucun verrou .git/index.lock."
        if not verrou else
        "Un .git/index.lock traîne : toute commande git reste bloquée "
        "derrière lui tant qu'il n'est pas supprimé.",
    )

    nb_mod = dossier.get("nb_modifies") or 0
    _critere(
        "modifies", "Fichiers modifiés non commités", nb_mod * 2, 10,
        "Rien en attente de commit."
        if not nb_mod else
        f"{nb_mod} fichier(s) modifié(s) dans le dossier de travail de "
        "l'instance — une promotion partirait sans eux.",
    )

    nb_non_suivis = dossier.get("nb_non_suivis") or 0
    _critere(
        "non_suivis", "Fichiers non suivis", nb_non_suivis * 0.2, 10,
        "Aucun fichier non suivi."
        if not nb_non_suivis else
        f"{nb_non_suivis} fichier(s) non suivi(s) — à ignorer via .gitignore "
        "ou à ranger hors du dépôt.",
    )

    perdu = sum(c["perdu"] for c in criteres)
    score = max(0, 100 - perdu)

    lettre, libelle = "E", "Dépôt à reprendre"
    for seuil, l, lib in (
        (90, "A", "Dépôt sain"),
        (75, "B", "Bon état"),
        (60, "C", "Ménage à prévoir"),
        (40, "D", "Ménage à faire"),
    ):
        if score >= seuil:
            lettre, libelle = l, lib
            break

    # Les critères qui coûtent le plus cher en premier : c'est l'ordre dans
    # lequel on veut lire la liste quand on cherche quoi corriger.
    criteres.sort(key=lambda c: (-c["perdu"], c["label"]))
    return {
        "score": score,
        "lettre": lettre,
        "libelle": libelle,
        "perdu": perdu,
        "criteres": criteres,
    }


@router.get("/api/deploiement/sante")
def deploiement_sante(request: Request):
    """Migrations, branches et propreté du dossier — consultation seule."""
    require_settings(request)

    # D'abord rafraîchir, ensuite lire : l'ordre inverse afficherait l'état du
    # dernier fetch, pas l'état réel du dépôt distant.
    refs_a_jour = _git_rafraichir_refs()

    def _sans_casser(fn, defaut):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — vue de consultation
            print(f"[MySifa] santé du dépôt — {fn.__name__} indisponible : {exc}")
            return defaut

    migrations = _sans_casser(_migrations_etat, {
        "appliquees": [], "nb_appliquees": 0, "derniere": None,
        "en_attente": [], "nb_fichiers": 0, "doublons": [],
    })
    branches = _sans_casser(_branches_etat, [])
    dossier = _sans_casser(_dossier_etat, {
        "branche": "?", "nb_modifies": 0, "nb_non_suivis": 0,
        "modifies": [], "non_suivis": [], "verrou_git": False, "propre": True,
    })

    alertes: list[str] = []
    if migrations["en_attente"]:
        alertes.append(
            f"{len(migrations['en_attente'])} migration(s) présente(s) dans le code mais "
            "pas encore appliquée(s) sur cette instance."
        )
    if migrations["doublons"]:
        alertes.append(
            f"{len(migrations['doublons'])} numéro(s) de migration en double dans l'historique — "
            "la seconde de chaque paire ne s'est jamais exécutée."
        )
    a_nettoyer = [b for b in branches if b["a_nettoyer"]]
    if a_nettoyer:
        alertes.append(
            f"{len(a_nettoyer)} branche(s) fusionnée(s) dans staging et sans activité "
            "depuis plus de deux semaines."
        )
    if dossier["verrou_git"]:
        alertes.append("Un verrou git traîne dans le dépôt (.git/index.lock).")
    if dossier["nb_modifies"]:
        alertes.append(f"{dossier['nb_modifies']} fichier(s) modifié(s) non commité(s).")
    if not refs_a_jour:
        alertes.append(
            "Les références distantes n'ont pas pu être rafraîchies : la liste "
            "des branches ci-dessous peut être périmée."
        )

    try:
        note = _note_sante(migrations, branches, dossier)
    except Exception as exc:  # noqa: BLE001 — vue de consultation
        print(f"[MySifa] santé du dépôt — note indisponible : {exc}")
        note = None

    return {
        "instance": ENV_NAME,
        "version_app": APP_VERSION,
        "refs_a_jour": refs_a_jour,
        "note": note,
        "migrations": migrations,
        "branches": branches,
        "dossier": dossier,
        "alertes": alertes,
    }


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


# ─── Historique des promotions ─────────────────────────────────────────────────
# Deux sources, fusionnées :
#   1. La table promotion_history de la DB v2, écrite par promote_v2.sh à chaque
#      déploiement (succès, rollback, échec). Source de vérité : dates de
#      déploiement réelles, notes de release, statut, commits figés.
#   2. Un backfill lu dans le dépôt git v2 : chaque merge « promote: merge
#      staging into main » sur origin/main correspond à une promotion passée,
#      antérieure à la mise en place de la table. Permet d'avoir un historique
#      non vide dès le premier jour.
#
# La DB lue est TOUJOURS celle de v2 (c'est v2 qui est promue), même quand
# l'endpoint est servi par v1 : les deux tournent sur la même machine. Ouverture
# en lecture seule pour ne jamais interférer avec la production. Repli sur la DB
# locale si le fichier v2 est absent (poste de dev).

V2_DB_PATH = f"{V2_REPO_PATH}/app/data/production.db"

# Sujet du commit de merge généré par promote_v2.sh — clé du backfill git.
_PROMOTE_MERGE_SUBJECT = "promote: merge staging into main"


def _promote_history_from_db() -> list:
    """Lit promotion_history dans la DB v2 (lecture seule). [] si indisponible."""
    import json as _json
    import sqlite3 as _sqlite3

    rows = []
    try:
        conn = _sqlite3.connect(f"file:{V2_DB_PATH}?mode=ro", uri=True, timeout=5)
    except Exception:
        try:
            from database import get_db
            with get_db() as local:
                cur = local.execute(
                    "SELECT * FROM promotion_history ORDER BY started_at DESC LIMIT 100"
                )
                raw = [dict(r) for r in cur.fetchall()]
        except Exception:
            return []
    else:
        try:
            conn.row_factory = _sqlite3.Row
            raw = [dict(r) for r in conn.execute(
                "SELECT * FROM promotion_history ORDER BY started_at DESC LIMIT 100"
            ).fetchall()]
        except Exception:
            return []
        finally:
            conn.close()

    for r in raw:
        try:
            commits = _json.loads(r.get("commits") or "[]")
        except Exception:
            commits = []
        rows.append({
            "source": "db",
            "date": r.get("started_at"),
            "finished_at": r.get("finished_at"),
            "statut": r.get("statut") or "success",
            "version_avant": r.get("version_avant"),
            "version": r.get("version_apres"),
            "head_avant": (r.get("head_avant") or "")[:7],
            "head": (r.get("head_apres") or "")[:7],
            "head_full": r.get("head_apres") or "",
            "commits_count": r.get("commits_count") or len(commits),
            "commits": commits,
            "notes": r.get("notes"),
            "message": r.get("message"),
            "auteur": r.get("declencheur") or "promote-bot",
        })
    return rows


def _promote_history_from_git(limit: int = 30) -> list:
    """Reconstruit l'historique des promotions passées depuis les merges git."""
    def _git(*args, timeout=15):
        return _subprocess.check_output(
            [_GIT_BIN, "-C", V2_REPO_PATH, *args], text=True, timeout=timeout,
        )

    try:
        merges_out = _git(
            "log", "origin/main", "--merges", "--grep", _PROMOTE_MERGE_SUBJECT,
            f"--max-count={limit}", "--pretty=format:%H|%h|%an|%ad",
            "--date=format:%Y-%m-%dT%H:%M:%S",
        )
    except Exception:
        return []

    releases = []
    for line in merges_out.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) != 4:
            continue
        full, short, author, date = parts

        # Les commits de la release = ceux apportés par staging (2e parent)
        # et absents de main avant le merge (1er parent).
        commits = []
        try:
            log_out = _git(
                "log", f"{full}^1..{full}^2", "--no-merges",
                "--pretty=format:%h|%an|%ad|%s", "--date=format:%Y-%m-%d %H:%M",
            )
            for cline in log_out.strip().split("\n"):
                if not cline:
                    continue
                cparts = cline.split("|", 3)
                if len(cparts) == 4:
                    commits.append({
                        "hash": cparts[0], "author": cparts[1],
                        "date": cparts[2], "subject": cparts[3],
                    })
        except Exception:
            pass

        version = None
        try:
            version = _parse_version_from_text(_git("show", f"{full}:config.py", timeout=10))
        except Exception:
            pass

        releases.append({
            "source": "git",
            "date": date,
            "finished_at": None,
            "statut": "success",
            "version_avant": None,
            "version": version,
            "head_avant": "",
            "head": short,
            "head_full": full,
            "commits_count": len(commits),
            "commits": commits,
            "notes": None,
            "message": None,
            "auteur": author,
        })

    # version_avant : la version de la release précédente (git est trié récent → ancien)
    for i, rel in enumerate(releases):
        if i + 1 < len(releases):
            rel["version_avant"] = releases[i + 1]["version"]
            rel["head_avant"] = releases[i + 1]["head"]
    return releases


@router.get("/api/promote/history")
def promote_history(request: Request, limit: int = 30):
    require_settings(request)

    db_rows = _promote_history_from_db()
    git_rows = _promote_history_from_git(limit=limit)

    # Dédoublonnage : après une promotion, le HEAD de v2 est exactement le commit
    # de merge « promote: … ». Une release déjà en base n'est donc pas reprise du git.
    known = {r["head_full"] for r in db_rows if r.get("head_full")}
    known |= {r["head"] for r in db_rows if r.get("head")}
    merged = db_rows + [
        g for g in git_rows
        if g["head_full"] not in known and g["head"] not in known
    ]
    merged.sort(key=lambda r: (r.get("date") or ""), reverse=True)

    return {
        "env": ENV_NAME,
        "count": len(merged),
        "has_db_rows": bool(db_rows),
        "releases": merged[:limit],
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
    # v229 : rattachement pièce d'usure. usure_piece_id NULL = pas une pièce
    # d'usure — c'est le flag lui-même, il n'y a pas de booléen séparé.
    try:
        _upid = r["usure_piece_id"]
        usure_piece_id = int(_upid) if _upid is not None else None
    except (IndexError, KeyError, TypeError, ValueError):
        usure_piece_id = None
    try:
        usure_position = r["usure_position"] or ""
    except (IndexError, KeyError):
        usure_position = ""
    # v2.7.1 : archived_at. Un code encore utilise n'est plus supprime mais
    # archive — il sort du catalogue sans orpheliner l'historique.
    try:
        archived_v = r["archived_at"] or None
    except (IndexError, KeyError):
        archived_v = None
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
        "usure_piece_id": usure_piece_id,
        "usure_position": usure_position if usure_piece_id is not None else "",
        "archived_at": archived_v,
        "archived": bool(archived_v),
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


def _maint_code_usages(conn, code: str) -> dict:
    """Compte ce qui serait orpheline par la suppression du code.

    Le total conditionne le comportement de DELETE : zero usage = suppression
    reelle, sinon archivage. On regarde les saisies ET les modeles de creneau :
    supprimer un code encore reference par un modele casserait la planification
    aussi surement qu'il casserait l'historique.
    """
    def _count(sql: str) -> int:
        try:
            row = conn.execute(sql, (code,)).fetchone()
            return int(row["n"] or 0) if row else 0
        except Exception:
            return 0  # table absente sur une DB pas encore migree
    saisies = _count(
        "SELECT COUNT(*) AS n FROM maintenance_event_ops WHERE code = ?")
    modeles = _count(
        "SELECT COUNT(*) AS n FROM maintenance_template_ops WHERE code = ?")
    docs = _count(
        "SELECT COUNT(*) AS n FROM maintenance_docs WHERE code = ?")
    return {
        "saisies": saisies,
        "modeles": modeles,
        "docs": docs,
        "total": saisies + modeles,
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
    # v229 — Rattachement à une pièce d'usure. usure_piece_id NULL = code
    # ordinaire. La cohérence (pièce existante, position déclarée sur la pièce,
    # couple non déjà pris) est vérifiée par _validate_usure_link, qui a besoin
    # d'une connexion : elle est appelée par les endpoints, pas ici.
    _raw_piece = body.get("usure_piece_id")
    if _raw_piece in (None, "", "null"):
        usure_piece_id = None
    else:
        try:
            usure_piece_id = int(_raw_piece)
        except (TypeError, ValueError):
            raise HTTPException(422, "Pièce d'usure invalide.")
        if usure_piece_id <= 0:
            usure_piece_id = None
    # Jamais NULL quand la pièce est renseignée : l'index unique partiel
    # considérerait deux NULL comme distincts et laisserait passer un doublon.
    #
    # v230 : la position est désormais saisie librement SUR LE CODE (elle n'est
    # plus choisie dans une liste déclarée sur la pièce). On la stocke en
    # minuscules : c'est une clé — index unique, cache front, localStorage de
    # l'onglet mémorisé. « Bande » et « bande » doivent être la même position,
    # sinon la carte afficherait deux onglets pour la même chose. L'affichage
    # remet la majuscule initiale.
    usure_position = (body.get("usure_position") or "").strip().lower()
    if len(usure_position) > 40:
        usure_position = usure_position[:40]
    if usure_piece_id is None:
        usure_position = ""
    if usure_position:
        import re as _re_pos
        # Même charset que l'ancien référentiel : la position sert d'étiquette
        # d'onglet ET de clé, on évite d'avoir à l'échapper partout.
        if not _re_pos.fullmatch(r"[a-z0-9][a-z0-9 _-]*", usure_position):
            raise HTTPException(
                422,
                f"Position « {usure_position} » invalide : lettres non accentuées, "
                "chiffres, espace, tiret et underscore uniquement.",
            )

    # Référence métrage : texte libre (ex. "5000 m"). v229 — devenue EXCLUSIVE
    # aux pièces d'usure. Elle n'a jamais été lue ailleurs (seule la carte
    # pièce d'usure la consomme) : on cesse simplement de l'accepter sur un
    # code non rattaché, au lieu de la stocker pour rien.
    metrage_ref = (body.get("metrage_ref") or "").strip()
    if len(metrage_ref) > 80:
        metrage_ref = metrage_ref[:80]
    if usure_piece_id is None:
        metrage_ref = ""
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
        "usure_piece_id": usure_piece_id,
        "usure_position": usure_position,
    }


# ─── Pièces d'usure — référentiel + validation du rattachement ────────────────
# Une « pièce d'usure » (Couteaux, Contre-couteaux…) regroupe un ou plusieurs
# codes maintenance sous une seule carte de l'accueil Maintenance. Quand la
# pièce déclare des positions (Bande / Rive…), chaque position est portée par
# un code distinct : c'est ce qui permet à une carte d'avoir des onglets sans
# que le code ait à deviner quoi que ce soit à partir des libellés.

def _usure_positions_from_codes(conn, piece_id: int) -> list:
    """Positions RÉELLEMENT en usage sur une pièce, déduites de ses codes.

    v230 — inversion du modèle. Les positions étaient déclarées sur la pièce
    (colonne `positions`, JSON) et le code en choisissait une. Elles sont
    maintenant saisies librement sur le code, et la pièce ne fait que les
    refléter. Conséquence voulue : une position ne peut plus exister sans code,
    donc plus de carte fantôme « pièce · position » sans opération derrière —
    c'est exactement le cas qui rendait l'écran incompréhensible après la
    suppression d'un code.

    La colonne `positions` de maintenance_usure_pieces n'est plus lue ni
    écrite. Elle est conservée en base (donnée historique, aucun coût) plutôt
    que supprimée : un DROP COLUMN n'est pas disponible sur toutes les
    versions de SQLite déployées.
    """
    rows = conn.execute(
        """SELECT DISTINCT COALESCE(usure_position,'') AS pos
           FROM maintenance_codes
           WHERE usure_piece_id=? AND COALESCE(usure_position,'') <> ''
           ORDER BY pos""",
        (piece_id,),
    ).fetchall()
    return [r["pos"] for r in rows]


def _usure_piece_row_to_dict(row, codes_count: int = 0, positions=None) -> dict:
    return {
        "id": int(row["id"]),
        "cle": row["cle"],
        "label": row["label"],
        # v230 : reflet des positions en usage, jamais une liste déclarée.
        "positions": list(positions or []),
        "ordre": int(row["ordre"] or 0),
        "actif": bool(row["actif"]),
        "codes_count": codes_count,
    }


def _ensure_usure_table(conn) -> bool:
    """True si la migration v229 a bien tourné sur cette instance."""
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='maintenance_usure_pieces'"
    ).fetchone())


def _validate_usure_link(conn, data: dict, current_code: str = "") -> None:
    """Vérifie le couple (pièce, position) avant écriture d'un code.

    v230 — la position n'est plus validée contre une liste déclarée sur la
    pièce (elle est saisie librement). Restent trois refus, tous explicites :
      - la pièce n'existe pas / est désactivée
      - le couple (pièce, position) est déjà porté par un autre code
      - la pièce mélangerait des codes avec et sans position

    Le dernier point mérite un mot : une carte est soit à onglets, soit sans
    onglet. Un code sans position sur une pièce qui en a déjà (ou l'inverse)
    donnerait une carte dont une partie du contenu serait inatteignable.
    """
    piece_id = data.get("usure_piece_id")
    if piece_id is None:
        return
    # v231 : réservé à la catégorie Interventions. C'est la seule dont les
    # cartes remontent sur l'accueil Maintenance (showWearParts est conditionné
    # au filtre « Remplacements ») : un code rattaché ailleurs porterait un
    # rattachement que personne ne verrait jamais.
    if (data.get("categorie") or "") != "remplacements":
        raise HTTPException(
            422,
            "Le rattachement à une pièce d'usure n'est possible que sur la "
            "catégorie Interventions.",
        )
    if not _ensure_usure_table(conn):
        raise HTTPException(
            500, "Migration DB manquante (maintenance_usure_pieces absente)."
        )
    row = conn.execute(
        "SELECT id, cle, label, ordre, actif FROM maintenance_usure_pieces WHERE id=?",
        (piece_id,),
    ).fetchone()
    if not row:
        raise HTTPException(422, "Pièce d'usure introuvable.")
    if not row["actif"]:
        raise HTTPException(422, f"La pièce « {row['label']} » est désactivée.")
    pos = data.get("usure_position") or ""
    # Cohérence du mode : la pièce est à onglets ou elle ne l'est pas.
    others = conn.execute(
        """SELECT code, label, COALESCE(usure_position,'') AS pos
           FROM maintenance_codes
           WHERE usure_piece_id=? AND code<>?""",
        (piece_id, current_code or ""),
    ).fetchall()
    if others:
        others_positioned = any((o["pos"] or "") for o in others)
        if pos and not others_positioned:
            _o = others[0]
            raise HTTPException(
                422,
                f"« {row['label']} » est déjà porté par le code {_o['code']} sans position. "
                "Une pièce a soit des positions sur tous ses codes, soit aucune : "
                f"ajoutez une position au code {_o['code']}, ou retirez celle-ci.",
            )
        if not pos and others_positioned:
            _named = ", ".join(f"{o['code']} ({o['pos']})" for o in others if o["pos"])
            raise HTTPException(
                422,
                f"« {row['label']} » a déjà des positions ({_named}). "
                "Renseignez une position pour ce code, ou retirez-la des autres.",
            )
    clash = conn.execute(
        """SELECT code, label FROM maintenance_codes
           WHERE usure_piece_id=? AND COALESCE(usure_position,'')=? AND code<>?
           LIMIT 1""",
        (piece_id, pos, current_code or ""),
    ).fetchone()
    if clash:
        _where = f"« {row['label']} · {pos.capitalize()} »" if pos else f"« {row['label']} »"
        raise HTTPException(
            409,
            f"{_where} est déjà rattaché au code {clash['code']} ({clash['label']}).",
        )


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
# v2.5.6 : « manual » n'est plus proposé dans le formulaire. Il ne portait
# aucune sémantique runtime (jamais évalué par /alerts/active) : une alerte
# réglée sur "manuel" ne s'affichait donc JAMAIS chez l'opérateur. On continue
# de l'ACCEPTER en entrée pour ne pas casser la relecture / le réenregistrement
# des alertes historiques qui le portent encore en base (aucune migration :
# ces alertes restent dormantes tant que l'admin ne choisit pas un vrai type).
_ALERT_TRIGGER_TYPES = {"manual", "periodic", "calendar", "event"}
_ALERT_TRIGGER_TYPES_DEPRECATED = {"manual"}
_ALERT_TRIGGER_EVENTS = {"dossier_start", "dossier_end", "machine_change", "login", "after_calage"}

# v2.3.2 : codes considérés comme "calage" pour l'alerte after_calage.
# Liste synchronisée avec la sidebar CALAGE de /prod. On préfère matcher
# par code exact (operation_code IN ...) plutôt que par operation_category
# car les codes 82/83/84/85/91 n'ont pas de category dans operations.json.
_ALERT_CALAGE_CODES = frozenset({
    "02",  # Calage
    "10",  # Calage Errepi
    "11",  # Calage Bunsch
    "12",  # Changement de couleur
    "58",  # Changement bobines
    "59",  # Changement Contre-Partie
    "60",  # Changement Plaque
    "74",  # Changement Magnétique
    "75",  # Changement Cliché
    "82",  # Changement couteaux bande
    "83",  # Changement couteaux rive
    "84",  # Changement contre couteaux bande
    "85",  # Changement contre couteaux rive
    "91",  # Changement Anilox
})
_ALERT_CALAGE_CODES_SQL_LIST = "(" + ",".join(f"'{c}'" for c in sorted(_ALERT_CALAGE_CODES)) + ")"

# v2.5.6 : codes qui marquent la REPRISE de production apres un calage. Ce sont
# eux qui declenchent l'alerte after_calage -- l'alerte doit sortir a la FIN du
# calage (premier code de production), pas a son debut. Meme couple que le
# garde-fou HTTP 423 de /api/fabrication/saisie (cf. fabrication.py).
_ALERT_POST_CALAGE_CODES = frozenset({
    "03",  # Production
    "88",  # Reprise
})
_ALERT_POST_CALAGE_CODES_SQL_LIST = "(" + ",".join(f"'{c}'" for c in sorted(_ALERT_POST_CALAGE_CODES)) + ")"
_ALERT_CALENDAR_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
# Ordre canonique, indexé comme datetime.weekday() (lundi = 0 … dimanche = 6).
_ALERT_CALENDAR_DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


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
    # v2.5.6 : défaut « periodic » (avant : « manual », qui ne déclenchait rien).
    t_type = (trig_in.get("type") or "periodic").strip()
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
        trig["days"] = [d for d in _ALERT_CALENDAR_DAY_ORDER if d in days]
        # Sémantique du déclenchement (v2.5.6, cf. _is_calendar_alert_due) :
        #   - L'alerte devient due à HH:MM les jours cochés, SANS condition de
        #     production : la machine peut être à l'arrêt, l'alerte s'affiche
        #     dès qu'un opérateur ciblé ouvre son écran (contrôle de prise de
        #     poste typiquement).
        #   - Elle reste due tant qu'elle n'est pas validée (ou esquivée), y
        #     compris les jours suivants — pas de fenêtre d'expiration.
        #   - Le compteur est par machine : chaque machine ciblée doit valider.
        #   - Jamais rétroactive : une occurrence antérieure à la création de
        #     l'alerte est ignorée.
        #   - v2.5.7 : l'affichage respecte le délai entre alertes
        #     (min_gap_minutes) ; le blocage 03/88 d'une calendaire bloquante,
        #     lui, reste immédiat.
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
    # type=manual : déclencheur obsolète (v2.5.6), conservé en lecture seule
    # pour les alertes historiques. Aucun param supplémentaire, aucune
    # évaluation runtime — l'alerte reste dormante.
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
    # v2.3.33 : le libellé du bouton Valider n'est plus paramétrable côté
    # admin — figé à « Valider » pour toutes les alertes. Ancien
    # `validation.button_label` custom (ex. « OK ») est écrasé au prochain
    # save. On accepte encore l'objet en entrée pour rétro-compat mais on
    # ignore son contenu.
    out["validation"] = {"button_label": "Valider"}

    # v2.2.88 : block_production par alerte (défaut False). Quand True,
    # la modale s'affiche avec backdrop bloquant et le backend refuse toute
    # saisie de production tant que l'alerte n'est pas ack.
    out["block_production"] = bool(params.get("block_production", False))

    # v2.3.12 : placement et size par alerte (au lieu du singleton global).
    _valid_placements = {"top-right", "center"}  # v2.3.17 : bottom-right retiré
    _valid_sizes = {"small", "medium", "large"}
    _p = str(params.get("placement", "") or "").strip()
    if _p in _valid_placements:
        out["placement"] = _p
    _s = str(params.get("size", "") or "").strip()
    if _s in _valid_sizes:
        out["size"] = _s

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
        # v2.5.21 : comment_responses — sous-ensemble des réponses proposées
        # qui, lorsqu'elles sont cochées par l'opérateur, déclenchent une zone
        # de commentaire OBLIGATOIRE sous le point de contrôle. Tant qu'elle
        # est vide, le bouton Valider reste bloqué côté runtime. Même forme et
        # même normalisation que nc_responses : on ne conserve que des libellés
        # qui existent réellement dans clean_responses, pour qu'un renommage de
        # réponse côté admin ne laisse pas de référence orpheline.
        com_in = it.get("comment_responses") or []
        clean_com = []
        if isinstance(com_in, list):
            _resp_set = set(clean_responses)
            seen_com = set()
            for r in com_in:
                if not isinstance(r, str):
                    continue
                rs = r.strip()[:100]
                if rs and rs in _resp_set and rs not in seen_com:
                    clean_com.append(rs)
                    seen_com.add(rs)
        # v2.5.21 : other_needs_comment — même mécanique appliquée à la réponse
        # « Autre ». Pertinent uniquement quand allow_other est activé.
        other_needs_comment = bool(it.get("other_needs_comment", False)) and allow_other
        # v2.2.85 : required (bool). Défaut false.
        required_choice = bool(it.get("required", False))
        _choice_item = {"type": "choice", "label": label,
                        "responses": clean_responses, "multi": multi,
                        "allow_other": allow_other,
                        "other_is_nc": other_is_nc,
                        "nc_responses": clean_nc,
                        "comment_responses": clean_com,
                        "other_needs_comment": other_needs_comment}
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
def maintenance_codes_list(request: Request, include_libres: int = 0,
                           include_archived: int = 0):
    """Liste des codes maintenance du catalogue standard.
    Depuis v180, les codes libres (libre=1) sont exclus par defaut. Pour les
    inclure (ex. panneau admin dedié), passer include_libres=1.
    Depuis v2.7.1, les codes archives sont exclus par defaut : ils ne doivent
    plus etre proposes a la saisie, mais leur ligne reste en base pour que
    l'historique continue de resoudre leur libelle. include_archived=1 les
    ramene (panneau catalogue, filtre « archives »).
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
        # v229 : rattachement pièce d'usure (absent des DB pas encore migrées).
        if "usure_piece_id" in cols: sel_extra += ",usure_piece_id"
        if "usure_position" in cols: sel_extra += ",usure_position"
        has_archived = "archived_at" in cols
        if has_archived: sel_extra += ",archived_at"
        conds = []
        if has_libre and not include_libres:
            conds.append("libre = 0")
        if has_archived and not include_archived:
            conds.append("archived_at IS NULL")
        where = ("WHERE " + " AND ".join(conds)) if conds else ""
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
        _ecols = {c["name"] for c in conn.execute(
            "PRAGMA table_info(maintenance_codes)").fetchall()}
        _arch_sel = ",archived_at" if "archived_at" in _ecols else ""
        existing = conn.execute(
            f"SELECT label{_arch_sel} FROM maintenance_codes WHERE code=? LIMIT 1",
            (data["code"],),
        ).fetchone()
        if existing:
            # v2.7.1 : un identifiant archive n'est pas « libre ». Le laisser
            # se recreer, c'est exactement le bug qu'on corrige : les saisies
            # de l'ancien code se rattachaient au nouveau libelle et
            # l'historique affichait une intervention qui n'a jamais eu lieu.
            _arch = None
            if _arch_sel:
                try:
                    _arch = existing["archived_at"]
                except (IndexError, KeyError):
                    _arch = None
            if _arch:
                raise HTTPException(409, {
                    "message": (
                        f"Le code {data['code']} a ete archive (il porte encore "
                        f"des saisies). Reactive-le au lieu de le recreer, ou "
                        f"choisis un autre identifiant."
                    ),
                    "archived": True,
                    "code": data["code"],
                    "label": existing["label"],
                })
            raise HTTPException(409, f"Le code {data['code']} existe deja.")
        _validate_usure_link(conn, data)
        _cols = {c["name"] for c in conn.execute(
            "PRAGMA table_info(maintenance_codes)").fetchall()}
        _names = ["code", "label", "niveau", "categorie", "periodique",
                  "intervalle", "metrage_ref", "created_at", "updated_at"]
        _values = [data["code"], data["label"], data["niveau"], data["categorie"],
                   data["periodique"], data["intervalle"], data["metrage_ref"], now, now]
        if "usure_piece_id" in _cols:
            _names.append("usure_piece_id"); _values.append(data["usure_piece_id"])
        if "usure_position" in _cols:
            _names.append("usure_position"); _values.append(data["usure_position"])
        conn.execute(
            "INSERT INTO maintenance_codes (%s) VALUES (%s)"
            % (",".join(_names), ",".join("?" * len(_names))),
            _values,
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
        _validate_usure_link(conn, data, current_code=data["code"])
        _cols = {c["name"] for c in conn.execute(
            "PRAGMA table_info(maintenance_codes)").fetchall()}
        _sets = ["label=?", "niveau=?", "categorie=?", "periodique=?",
                 "intervalle=?", "metrage_ref=?", "updated_at=?"]
        _values = [data["label"], data["niveau"], data["categorie"],
                   data["periodique"], data["intervalle"], data["metrage_ref"], now]
        if "usure_piece_id" in _cols:
            _sets.append("usure_piece_id=?"); _values.append(data["usure_piece_id"])
        if "usure_position" in _cols:
            _sets.append("usure_position=?"); _values.append(data["usure_position"])
        _values.append(data["code"])
        cur = conn.execute(
            "UPDATE maintenance_codes SET %s WHERE code=?" % ", ".join(_sets),
            _values,
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
    """Supprime un code — ou l'archive s'il porte deja des saisies.

    Avant v2.7.1, cette route faisait un DELETE sec sur maintenance_codes.
    Les saisies de maintenance_event_ops y survivaient (la cle etrangere est
    inerte : get_db() n'active pas PRAGMA foreign_keys=ON), et l'historique,
    qui resout le libelle a la volee par LEFT JOIN sur le code, les affichait
    avec le code brut. Recreer le meme identifiant les rattachait au nouveau
    libelle : l'historique racontait alors une intervention qui n'avait jamais
    eu lieu.

    Regle desormais : zero usage = suppression reelle (identifiant
    immediatement reutilisable) ; au moins une saisie ou un modele = archivage.
    Le code sort du catalogue, son libelle continue de resoudre dans
    l'historique, et l'identifiant reste pris tant qu'il n'est pas reactive.
    C'est le meme garde-fou que celui deja en place sur les interventions
    libres (maintenance_libres_delete).
    """
    user = _require_maint_writer(request)
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        row = conn.execute(
            "SELECT label FROM maintenance_codes WHERE code=? LIMIT 1", (code,)
        ).fetchone()
        if not row:
            raise HTTPException(404, f"Code {code} introuvable.")
        usages = _maint_code_usages(conn, code)
        has_archived = "archived_at" in {
            c["name"] for c in conn.execute(
                "PRAGMA table_info(maintenance_codes)").fetchall()}
        if usages["total"] > 0 and has_archived:
            conn.execute(
                "UPDATE maintenance_codes SET archived_at=?, updated_at=? WHERE code=?",
                (now, now, code),
            )
            conn.commit()
            log_action(user=user, action="ARCHIVE", module="maintenance_codes",
                       objet=code,
                       detail=f"{row['label']} — {usages['saisies']} saisie(s), "
                              f"{usages['modeles']} modele(s)")
            return {"ok": True, "archived": True, "code": code,
                    "label": row["label"], "usages": usages}
        # Aucun usage : suppression reelle. On purge au passage les documents
        # attaches, dont le ON DELETE CASCADE declare est tout aussi inerte
        # que la cle etrangere des saisies.
        try:
            conn.execute("DELETE FROM maintenance_docs WHERE code=?", (code,))
        except Exception:
            pass  # table absente sur une DB pas encore migree
        conn.execute("DELETE FROM maintenance_codes WHERE code=?", (code,))
        # v2.2.15 — Plus de cascade sur les alertes (le système auto a été
        # retiré). Les alertes classiques (manuelles) ne sont jamais liées
        # à un code, donc rien à supprimer côté maintenance_alerts.
        conn.commit()
    log_action(user=user, action="DELETE", module="maintenance_codes",
               objet=code, detail="")
    return {"ok": True, "archived": False, "code": code}


@router.post("/api/maintenance/codes/{code}/restore")
def maintenance_codes_restore(code: str, request: Request):
    """Reactive un code archive : il repasse dans le catalogue avec son
    historique. C'est la sortie de secours quand l'archivage a ete fait par
    erreur, ou quand l'operation redevient d'actualite."""
    user = _require_maint_writer(request)
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        cols = {c["name"] for c in conn.execute(
            "PRAGMA table_info(maintenance_codes)").fetchall()}
        if "archived_at" not in cols:
            raise HTTPException(400, "Base pas encore migree (archived_at absent).")
        row = conn.execute(
            "SELECT label, archived_at FROM maintenance_codes WHERE code=? LIMIT 1",
            (code,),
        ).fetchone()
        if not row:
            raise HTTPException(404, f"Code {code} introuvable.")
        if not row["archived_at"]:
            return {"ok": True, "code": code, "already_active": True}
        conn.execute(
            "UPDATE maintenance_codes SET archived_at=NULL, updated_at=? WHERE code=?",
            (now, code),
        )
        conn.commit()
    log_action(user=user, action="RESTORE", module="maintenance_codes",
               objet=code, detail=row["label"])
    return {"ok": True, "code": code, "label": row["label"]}


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


# ─── v2.5.11 : rattachement / transformation des interventions libres ──
#
# Deux actions admin depuis MyMaintenance > Operations de maintenance >
# Gestion des operations > onglet Inhabituelles :
#
#   1. RATTACHER  (attach)  — le titre libre etait en fait une operation du
#      catalogue mal nommee par l'operateur. Toutes ses saisies basculent sur
#      le code recurrent cible, le titre libre disparait. Les saisies comptent
#      alors comme des saisies recurrentes classiques (carte Suivi machine,
#      derniere intervention, statut En retard / A jour).
#
#   2. TRANSFORMER (promote) — le titre libre decrit une vraie operation
#      recurrente absente du catalogue. Le code LIB-xxx devient un code
#      catalogue (nouveau code numerique, libre=0, periodique=1) et ses
#      saisies passees deviennent l'historique de la nouvelle recurrente.
#
# Les deux sont irreversibles hors SQL manuel (meme regle que la fusion
# LIB->LIB) et tracees dans le journal d'audit.

# Tables portant une reference texte vers maintenance_codes(code). Le PRAGMA
# foreign_keys n'etant pas actif globalement, le repointage est fait a la main.
_MAINT_CODE_REF_TABLES = (
    "maintenance_event_ops",
    "maintenance_docs",
    "maintenance_tasks",
    "maintenance_template_ops",
)


def _maint_table_exists(conn, table: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)
    ).fetchone())


def _maint_move_ops(conn, src_code: str, dst_code: str, now: str):
    """Deplace les saisies de src_code vers dst_code.

    La contrainte UNIQUE(event_id, code) de maintenance_event_ops interdit deux
    saisies du meme code dans un meme creneau : quand le creneau contient deja
    une saisie du code cible, les deux sont FUSIONNEES en une seule (choix
    produit) plutot que de faire echouer l'operation :
      - observations et pieces changees concatenees,
      - durees additionnees (les deux interventions ont bien eu lieu),
      - machines en union,
      - date/auteur/statut repris de la saisie la plus recente.

    Retourne (nb_deplacees, nb_fusionnees).
    """
    moved = 0
    merged = 0
    src_ops = conn.execute(
        "SELECT * FROM maintenance_event_ops WHERE code = ?", (src_code,)
    ).fetchall()
    for op in src_ops:
        tgt = conn.execute(
            "SELECT * FROM maintenance_event_ops WHERE event_id = ? AND code = ? LIMIT 1",
            (op["event_id"], dst_code),
        ).fetchone()
        if not tgt:
            conn.execute(
                "UPDATE maintenance_event_ops SET code = ?, updated_at = ? WHERE id = ?",
                (dst_code, now, op["id"]),
            )
            moved += 1
            continue
        # Collision : fusion des deux saisies dans la ligne cible.
        # Regles communes avec le reclassement depuis l'historique.
        merge_op_rows(conn, op, tgt, now)
        merged += 1
    # Autres tables referencant le code (docs, taches, ops de templates).
    for table in _MAINT_CODE_REF_TABLES:
        if table == "maintenance_event_ops" or not _maint_table_exists(conn, table):
            continue
        try:
            conn.execute(
                "UPDATE %s SET code = ? WHERE code = ?" % table, (dst_code, src_code)
            )
        except Exception:
            # Une contrainte d'unicite sur une table secondaire ne doit pas
            # faire echouer le rattachement des saisies.
            import logging as _logging
            _logging.warning("maint attach: repointage %s echoue (%s -> %s)",
                             table, src_code, dst_code)
    return moved, merged


@router.post("/api/maintenance/codes/libres/{code}/attach")
async def maintenance_libres_attach(code: str, request: Request):
    """Rattache un titre libre a un code recurrent existant.

    Body : {target_code}. Toutes les saisies du titre libre sont reaffectees
    au code cible (fusion en cas de collision de creneau), puis le code libre
    est supprime : il disparait de la liste des inhabituelles et de
    l'historique, ses saisies comptent comme des saisies recurrentes.
    Irreversible hors SQL manuel.
    """
    user = _require_maint_writer(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    target_code = (body.get("target_code") or "").strip()
    if not target_code:
        raise HTTPException(422, "target_code obligatoire.")
    if target_code == code:
        raise HTTPException(400, "Le code cible doit etre different du titre libre.")
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        src = conn.execute(
            "SELECT code, label, libre FROM maintenance_codes WHERE code = ?", (code,)
        ).fetchone()
        if not src:
            raise HTTPException(404, "Titre libre introuvable.")
        if not src["libre"]:
            raise HTTPException(400, "Ce code n'est pas une intervention libre.")
        tgt = conn.execute(
            "SELECT code, label, libre, periodique FROM maintenance_codes WHERE code = ?",
            (target_code,),
        ).fetchone()
        if not tgt:
            raise HTTPException(404, "Code recurrent cible introuvable.")
        if tgt["libre"]:
            raise HTTPException(
                400,
                "La cible est elle-meme une intervention libre : utilise la fusion.",
            )
        moved, merged = _maint_move_ops(conn, code, target_code, now)
        conn.execute("DELETE FROM maintenance_codes WHERE code = ?", (code,))
        conn.execute(
            "UPDATE maintenance_codes SET updated_at = ? WHERE code = ?",
            (now, target_code),
        )
        conn.commit()
    try:
        log_action(
            user=user, action="MERGE", module="maintenance_libres",
            objet=(
                "Rattachement %s (%s) -> %s (%s) : %d saisie(s) deplacee(s), "
                "%d fusionnee(s)" % (code, src["label"], target_code, tgt["label"],
                                     moved, merged)
            ),
            ip=request.client.host if request.client else None,
        )
    except Exception:
        pass
    return {
        "attached": code, "target": target_code,
        "moved": moved, "merged": merged, "total": moved + merged,
    }


@router.post("/api/maintenance/codes/libres/{code}/promote")
async def maintenance_libres_promote(code: str, request: Request):
    """Transforme un titre libre en code recurrent du catalogue.

    Body : {new_code, label, niveau, categorie, intervalle, metrage_ref}.
    Le code LIB-xxx est remplace par le nouveau code (PK), donc toutes ses
    saisies passees deviennent l'historique de la nouvelle operation
    recurrente : la carte Suivi machine affiche immediatement la derniere
    intervention et le bon statut. L'intervalle est obligatoire, sans lui la
    carte ne peut pas calculer d'echeance.
    """
    user = _require_maint_writer(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    payload = dict(body)
    payload["code"] = (body.get("new_code") or "").strip()
    data = _normalize_maint_payload(payload)
    if not data["intervalle"]:
        raise HTTPException(422, "Intervalle obligatoire pour une operation recurrente.")
    new_code = data["code"]
    if new_code == code:
        raise HTTPException(400, "Le nouveau code doit etre different du code libre.")
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        src = conn.execute(
            "SELECT code, label, libre, created_at FROM maintenance_codes WHERE code = ?",
            (code,),
        ).fetchone()
        if not src:
            raise HTTPException(404, "Titre libre introuvable.")
        if not src["libre"]:
            raise HTTPException(400, "Ce code n'est pas une intervention libre.")
        clash = conn.execute(
            "SELECT 1 FROM maintenance_codes WHERE code = ? LIMIT 1", (new_code,)
        ).fetchone()
        if clash:
            raise HTTPException(409, "Le code %s existe deja." % new_code)
        cols = {c["name"] for c in conn.execute(
            "PRAGMA table_info(maintenance_codes)").fetchall()}
        names = ["code", "label", "niveau", "categorie", "periodique",
                 "intervalle", "metrage_ref", "created_at", "updated_at"]
        values = [new_code, data["label"], data["niveau"], data["categorie"],
                  1, data["intervalle"], data["metrage_ref"],
                  src["created_at"] or now, now]
        if "libre" in cols:
            names.append("libre")
            values.append(0)
        if "usage_count" in cols:
            names.append("usage_count")
            values.append(0)
        # v229 : la promotion peut rattacher directement le nouveau code à une
        # pièce d'usure. Sans rattachement, _normalize_maint_payload a déjà vidé
        # metrage_ref — la référence métrage n'existe plus que pour ces pièces.
        _validate_usure_link(conn, data, current_code=new_code)
        if "usure_piece_id" in cols:
            names.append("usure_piece_id")
            values.append(data["usure_piece_id"])
        if "usure_position" in cols:
            names.append("usure_position")
            values.append(data["usure_position"])
        conn.execute(
            "INSERT INTO maintenance_codes (%s) VALUES (%s)"
            % (",".join(names), ",".join("?" * len(names))),
            values,
        )
        # Le nouveau code est neuf : aucune collision UNIQUE(event_id, code)
        # possible, _maint_move_ops se contente donc de repointer.
        moved, merged = _maint_move_ops(conn, code, new_code, now)
        conn.execute("DELETE FROM maintenance_codes WHERE code = ?", (code,))
        conn.commit()
    try:
        log_action(
            user=user, action="UPDATE", module="maintenance_libres",
            objet=(
                "Transformation %s (%s) -> code recurrent %s (%s) : "
                "%d saisie(s) reprises" % (code, src["label"], new_code,
                                           data["label"], moved + merged)
            ),
            ip=request.client.host if request.client else None,
        )
    except Exception:
        pass
    return {
        "promoted": code, "code": new_code, "label": data["label"],
        "moved": moved + merged,
    }


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


def _check_blocking_alert_due(conn, user, machine: str) -> list:
    """v2.3.5 — Retourne la LISTE des alertes bloquantes (block_production=True)
    actuellement dues pour cette machine (peut être vide). Utilisé par
    /api/fabrication/saisie comme garde-fou ET pour inclure directement l'alerte
    dans la réponse HTTP 423 → le front n'a plus besoin d'un endpoint séparé.

    Format des items identique à /alerts/active :
        {id, nom, params, linked_maint_code, no_dossier}
    """
    result = []
    if not machine:
        return result
    try:
        rows = conn.execute(
            "SELECT id, nom, params, linked_maint_code, created_at FROM maintenance_alerts WHERE active=1"
        ).fetchall()
    except Exception:
        return result
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
        # v2.3.4 : filtre machine strict (aligné avec /blocking-for-machine).
        # Le superadmin ne bypass plus — il faut que la machine soit dans la
        # cible sinon l'alerte n'a pas à se déclencher pour lui non plus.
        machines_target = target.get("machines")
        if not isinstance(machines_target, list) or not machines_target:
            legacy = target.get("machine")
            machines_target = [legacy] if isinstance(legacy, str) and legacy else ["*"]
        if "*" not in machines_target and user_machine not in machines_target:
            continue
        trig = params.get("trigger") or {}
        ttype = trig.get("type")
        if ttype == "periodic":
            try:
                if _is_periodic_alert_due(conn, int(r["id"]), params, machine, now_paris):
                    result.append({
                        "id": int(r["id"]),
                        "nom": r["nom"] if "nom" in r.keys() else "",
                        "params": params,
                        "linked_maint_code": (r["linked_maint_code"] if "linked_maint_code" in r.keys() else "") or "",
                        "no_dossier": "",
                    })
            except Exception:
                continue
        elif ttype == "calendar":
            # v2.5.6 : une alerte calendaire marquée "bloque la production"
            # doit aussi refuser la saisie tant qu'elle n'est pas validée.
            try:
                _created = r["created_at"] if "created_at" in r.keys() else None
                if _is_calendar_alert_due(
                    conn, int(r["id"]), params, machine, now_paris,
                    user_id=(user.get("id") if user else None),
                    created_at_iso=_created,
                ):
                    result.append({
                        "id": int(r["id"]),
                        "nom": r["nom"] if "nom" in r.keys() else "",
                        "params": params,
                        "linked_maint_code": (r["linked_maint_code"] if "linked_maint_code" in r.keys() else "") or "",
                        "no_dossier": "",
                    })
            except Exception:
                continue
        elif ttype == "event":
            event = str(trig.get("event") or "").strip()
            if event == "after_calage":
                # Réutilise la logique after_calage : dernière saisie machine = calage
                _calage_window = (now_paris - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%S")
                _window = (now_paris - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
                _last_row = conn.execute(
                    """SELECT no_dossier, operation_code, operation_category, date_operation
                       FROM production_data
                       WHERE machine=? AND date_operation >= ?
                       ORDER BY date_operation DESC LIMIT 1""",
                    (machine, _window),
                ).fetchone()
                if not _last_row:
                    continue
                # v2.3.2 : match par code exact (voir _ALERT_CALAGE_CODES)
                if str(_last_row["operation_code"] or "") not in _ALERT_CALAGE_CODES:
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
                result.append({
                    "id": int(r["id"]),
                    "nom": r["nom"] if "nom" in r.keys() else "",
                    "params": params,
                    "linked_maint_code": (r["linked_maint_code"] if "linked_maint_code" in r.keys() else "") or "",
                    "no_dossier": _dos,
                })
            # Autres events (dossier_start / dossier_end) : pas implémentés
            # comme bloquants pour l'instant. Reste ouvert pour extension.
    return result


@router.get("/api/maintenance/alerts/blocking-for-machine")
def maintenance_alerts_blocking_for_machine(request: Request, machine: str = ""):
    """v2.2.89 — Retourne la liste des alertes bloquantes actuellement dues
    pour une machine donnée. Appelé par le front après réception d'un HTTP 423
    sur /api/fabrication/saisie, pour afficher les alertes à l'écran.

    Format identique à /alerts/active pour que le runtime les affiche via
    la même fonction _renderAlert.
    """
    try:
        return _blocking_for_machine_impl(request, machine)
    except Exception as _err:
        import traceback
        print(f"[blocking-for-machine] FATAL: {_err}", flush=True)
        traceback.print_exc()
        # v2.3.3 : ne jamais renvoyer 500 — retourner liste vide pour ne pas
        # casser le flow front. L'erreur est loggée pour debug.
        return {"items": [], "_error": str(_err)}


def _blocking_for_machine_impl(request: Request, machine: str = ""):
    user = get_current_user(request)
    machine = (machine or "").strip()
    if not machine:
        # Fallback : machine liée à l'user
        with get_db() as conn:
            machine = _machine_name_from_user(conn, user) or ""
    items = []
    if not machine:
        return {"items": items}
    now_paris = datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    with get_db() as conn:
        try:
            rows = conn.execute(
                "SELECT id, nom, params, linked_maint_code, created_at FROM maintenance_alerts WHERE active=1"
            ).fetchall()
        except Exception:
            return {"items": items}
        user_role = user.get("role") if user else ""
        for r in rows:
            try:
                params = _json_alerts.loads(r["params"] or "{}")
            except (ValueError, TypeError):
                continue
            if not bool(params.get("block_production", False)):
                continue
            target = params.get("target") or {}
            # v2.2.90 : PAS de filtre operator_should_see_alert ici. Si l'user
            # est bloqué de saisir 03/88 côté serveur (423), il DOIT voir
            # l'alerte peu importe son rôle métier. Le filtre reste dans le
            # polling classique /alerts/active. On check seulement que la
            # machine cible correspond.
            machines_target = target.get("machines")
            if not isinstance(machines_target, list) or not machines_target:
                legacy = target.get("machine")
                machines_target = [legacy] if isinstance(legacy, str) and legacy else ["*"]
            if "*" not in machines_target and machine not in machines_target:
                continue
            trig = params.get("trigger") or {}
            ttype = trig.get("type")
            due = False
            trigger_no_dossier = ""
            if ttype == "periodic":
                try:
                    due = _is_periodic_alert_due(conn, int(r["id"]), params, machine, now_paris)
                except Exception:
                    due = False
            elif ttype == "calendar":
                # v2.5.6 : symétrique de _check_blocking_alert_due — une
                # calendaire bloquante non validée maintient le refus 423.
                try:
                    due = _is_calendar_alert_due(
                        conn, int(r["id"]), params, machine, now_paris,
                        user_id=(user.get("id") if user else None),
                        created_at_iso=(r["created_at"] if "created_at" in r.keys() else None),
                    )
                except Exception:
                    due = False
            elif ttype == "event":
                event = str(trig.get("event") or "").strip()
                if event == "after_calage":
                    _calage_window = (now_paris - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%S")
                    _window = (now_paris - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
                    _last_row = conn.execute(
                        """SELECT no_dossier, operation_code, operation_category, date_operation
                           FROM production_data
                           WHERE machine=? AND date_operation >= ?
                           ORDER BY date_operation DESC LIMIT 1""",
                        (machine, _window),
                    ).fetchone()
                    if (_last_row
                        and str(_last_row["operation_code"] or "") in _ALERT_CALAGE_CODES
                        and _last_row["no_dossier"]
                        and str(_last_row["no_dossier"]).strip()
                        and _last_row["date_operation"] >= _calage_window):
                        _dos = str(_last_row["no_dossier"]).strip()
                        _ack_check = conn.execute(
                            """SELECT 1 FROM maintenance_alert_acks
                               WHERE alert_id=? AND no_dossier=? LIMIT 1""",
                            (int(r["id"]), _dos),
                        ).fetchone()
                        if not _ack_check:
                            _last_89 = conn.execute(
                                """SELECT MAX(date_operation) AS m FROM production_data
                                   WHERE no_dossier=? AND machine=? AND operation_code='89'""",
                                (_dos, machine),
                            ).fetchone()
                            _last_89_at = _last_89["m"] if _last_89 else None
                            if not _last_89_at or _last_row["date_operation"] > _last_89_at:
                                due = True
                                trigger_no_dossier = _dos
            if due:
                items.append({
                    "id": int(r["id"]),
                    "nom": r["nom"] or "",
                    "params": params,
                    "linked_maint_code": r["linked_maint_code"] or "",
                    "no_dossier": trigger_no_dossier,
                })
    return {"items": items}


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
# Pour le type calendar (v2.5.6, cf. _is_calendar_alert_due) :
#   - Due à HH:MM les jours cochés, SANS condition de production (la machine
#     peut être à l'arrêt — cas d'usage : contrôle de prise de poste).
#   - Reste due jusqu'à validation ou esquive, y compris les jours suivants.
#     Une occurrence plus récente remplace la précédente, rien ne s'empile.
#   - Compteur par machine ; repli sur l'user_id si aucune machine résolue.
#   - Jamais rétroactive avant la création de l'alerte.
#   - v2.5.7 : respecte min_gap_minutes (comme le périodique). Pendant le
#     silence qui suit un ack sur la machine, l'alerte n'est pas poussée à
#     l'écran ; elle reste due et repart au premier poll après la fin du gap.
#     Le refus 423 sur saisie 03/88 ignore ce gap (cf. _blocking_for_machine).
#
# Pour le type event : implémenté (dossier_start / dossier_end / after_calage).
#
# Pour le type manual : OBSOLÈTE depuis v2.5.6. Retiré du formulaire, toujours
# accepté en lecture pour les alertes historiques, jamais évalué ici — une
# alerte encore réglée sur "manual" ne se déclenche donc jamais.


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


def _is_machine_in_production(conn, machine: str, exclude_saisie_id: int = None) -> bool:
    """True si la dernière saisie pour cette machine est code 01, 03 ou 88.

    v2.3.31 : exclude_saisie_id permet à _auto_ack_periodic_alerts_on_arret
    d'évaluer l'état de la machine *juste avant* la saisie qu'il traite,
    plutôt qu'après (la saisie non-productive vient d'être insérée et
    fausserait le calcul, faisant croire que la machine est déjà arrêtée).
    """
    if exclude_saisie_id is None:
        row = conn.execute(
            "SELECT operation_code FROM production_data "
            "WHERE machine=? ORDER BY date_operation DESC, id DESC LIMIT 1",
            (machine,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT operation_code FROM production_data "
            "WHERE machine=? AND id<>? ORDER BY date_operation DESC, id DESC LIMIT 1",
            (machine, int(exclude_saisie_id))
        ).fetchone()
    if not row:
        return False
    code = str(row["operation_code"] or "").strip()
    # v2.2.83 : 01 (Début prod) ne compte plus comme "en production"
    return code in ("03", "88")


def _is_periodic_alert_due(conn, alert_id: int, params: dict, machine: str, now_paris: datetime, exclude_saisie_id: int = None) -> bool:
    """Décide si une alerte périodique doit s'afficher maintenant pour cette machine.

    v2.3.31 : `exclude_saisie_id` (optionnel) exclut une ligne production_data
    de tous les calculs. Utilisé par _auto_ack_periodic_alerts_on_arret pour
    évaluer si l'alerte était due *avant* la saisie qu'il vient de traiter
    (sinon la saisie non-productive fausse le calcul et l'alerte apparaît
    toujours non-due, ce qui n'est pas la question posée).

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
    if not _is_machine_in_production(conn, machine, exclude_saisie_id=exclude_saisie_id):
        return False

    # v2.3.31 : morceau de SQL/params à ajouter pour exclure la saisie courante
    _excl_sql = " AND id<>?" if exclude_saisie_id is not None else ""
    _excl_params = (int(exclude_saisie_id),) if exclude_saisie_id is not None else ()

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
           AND operation_code IS NOT NULL AND operation_code != ''""" + _excl_sql,
        (machine,) + _excl_params,
    ).fetchone()
    last_stop_iso = last_stop_row["m"] if last_stop_row else None
    last_stop_dt = _parse_paris_dt(last_stop_iso)

    # 2. Début de la session courante : premier 01/03/88 après last_stop
    if last_stop_iso:
        session_row = conn.execute(
            """SELECT MIN(date_operation) AS m FROM production_data
               WHERE machine=? AND operation_code IN ('03', '88')
               AND date_operation > ?""" + _excl_sql,
            (machine, last_stop_iso) + _excl_params,
        ).fetchone()
    else:
        session_row = conn.execute(
            """SELECT MIN(date_operation) AS m FROM production_data
               WHERE machine=? AND operation_code IN ('03', '88')""" + _excl_sql,
            (machine,) + _excl_params,
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


def _last_calendar_occurrence(trig: dict, now_paris: datetime):
    """Dernière occurrence PASSÉE (ou en cours) d'un déclencheur calendaire.

    Exemple : trigger {time: "08:00", days: ["mon","tue","wed","thu","fri"]}
      - mardi 09:30 → mardi 08:00
      - mardi 07:15 → lundi 08:00 (l'occurrence du jour n'est pas encore due)
      - dimanche    → vendredi 08:00

    Retourne None si le trigger est invalide ou si aucun jour n'est coché.
    """
    time_str = str(trig.get("time") or "").strip()
    try:
        hh_s, mm_s = time_str.split(":")
        hh, mm = int(hh_s), int(mm_s)
        if not (0 <= hh < 24 and 0 <= mm < 60):
            return None
    except (ValueError, AttributeError):
        return None
    days = trig.get("days")
    if not isinstance(days, list) or not days:
        days = list(_ALERT_CALENDAR_DAY_ORDER)
    days_set = {d for d in days if d in _ALERT_CALENDAR_DAYS}
    if not days_set:
        return None
    # Remonter au plus 7 jours : on tombe forcément sur un jour coché.
    for delta in range(0, 8):
        d = now_paris - timedelta(days=delta)
        if _ALERT_CALENDAR_DAY_ORDER[d.weekday()] not in days_set:
            continue
        occ = d.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if occ <= now_paris:
            return occ
    return None


def _is_calendar_alert_due(
    conn,
    alert_id: int,
    params: dict,
    machine: str,
    now_paris: datetime,
    user_id=None,
    created_at_iso: str = None,
) -> bool:
    """Décide si une alerte calendaire doit s'afficher maintenant.

    v2.5.6 — Première implémentation réelle du type « calendaire ». Avant cette
    version le type était validé et stocké mais JAMAIS évalué : les alertes
    configurées à heure fixe ne se déclenchaient jamais.

    Règles (arbitrées avec l'admin) :
      1. Aucune condition de production — contrairement au périodique, la
         machine n'a pas besoin d'être en marche (03/88). L'usage visé est le
         contrôle de prise de poste, avant tout démarrage.
      2. Pas de fenêtre d'expiration — l'alerte reste due jusqu'à validation
         (ou esquive), y compris les jours suivants. Une occurrence plus
         récente remplace simplement la précédente : rien ne s'empile.
      3. Compteur par machine (comme le périodique). Si l'opérateur n'a pas de
         machine résolue, on retombe sur son user_id pour que deux opérateurs
         sans machine ne se neutralisent pas l'un l'autre.
      4. Jamais rétroactive : une occurrence antérieure à la création de
         l'alerte est ignorée (sinon une alerte créée à 14h « rattraperait »
         l'occurrence de 08h le jour même).

    Note (v2.5.7) : le délai de silence min_gap_minutes n'est PAS évalué ici.
    Cette fonction répond à « l'occurrence est-elle ouverte ? », pas à « faut-il
    l'afficher maintenant ? ». Le gap est appliqué par l'appelant :
    /alerts/active le respecte (l'alerte attend la fin du silence pour
    apparaître), _blocking_for_machine et _check_blocking_alert_due l'ignorent
    (une calendaire bloquante continue de refuser la saisie 03/88 pendant le
    gap — sinon le gap ouvrirait une fenêtre de contournement du contrôle).
    """
    trig = params.get("trigger") or {}
    if trig.get("type") != "calendar":
        return False
    occ = _last_calendar_occurrence(trig, now_paris)
    if occ is None:
        return False
    # 4. Plancher sur la création de l'alerte
    created_dt = _parse_paris_dt(created_at_iso)
    if created_dt is not None and occ < created_dt:
        return False
    # 3. Dernier ack (validation OU esquive : les deux insèrent une ligne dans
    #    maintenance_alert_acks, donc les deux referment l'occurrence).
    if machine:
        ack_row = conn.execute(
            "SELECT MAX(ack_at) AS m FROM maintenance_alert_acks "
            "WHERE alert_id=? AND machine=?",
            (alert_id, machine),
        ).fetchone()
    elif user_id is not None:
        ack_row = conn.execute(
            "SELECT MAX(ack_at) AS m FROM maintenance_alert_acks "
            "WHERE alert_id=? AND COALESCE(machine,'')='' AND user_id=?",
            (alert_id, user_id),
        ).fetchone()
    else:
        ack_row = conn.execute(
            "SELECT MAX(ack_at) AS m FROM maintenance_alert_acks "
            "WHERE alert_id=? AND COALESCE(machine,'')=''",
            (alert_id,),
        ).fetchone()
    last_ack_dt = _parse_paris_dt(ack_row["m"]) if ack_row else None
    # 2. Due tant que l'occurrence courante n'a pas été acquittée.
    return last_ack_dt is None or last_ack_dt < occ


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
        # Gap : calcule si un ack recent existe sur cette machine. Bloque les
        # alertes periodiques ET calendaires (v2.5.7) -- seules les alertes
        # evenementielles bypassent ce silence, car elles sont declenchees par
        # l'action metier de l'operateur (fin/debut de dossier). Sinon un
        # operateur qui clot un dossier juste apres un ack ne verrait jamais
        # l'alerte suivante.
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
            """SELECT id, nom, params, linked_maint_code, created_at
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
            # v2.3.10 : filtre machine strict — même pour superadmin, l'alerte
            # ne doit se déclencher que si la machine actuelle est ciblée.
            # Résout le bug : alerte Errepi (cible Cohésio 1) qui apparaissait
            # sur Cohésio 2 pour un superadmin.
            _machines_target = target.get("machines")
            if not isinstance(_machines_target, list) or not _machines_target:
                _legacy_m = target.get("machine")
                _machines_target = [_legacy_m] if isinstance(_legacy_m, str) and _legacy_m else ["*"]
            if "*" not in _machines_target and user_machine and user_machine not in _machines_target:
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
            elif ttype == "calendar":
                # v2.5.6 : implémenté. Aucune condition de production.
                # v2.5.7 : la calendaire respecte désormais min_gap_minutes,
                # comme la périodique (avant : bypass volontaire). Elle n'est
                # donc plus poussée à l'écran pendant le silence qui suit un
                # ack sur la machine — elle attend la fin du gap. Aucune
                # occurrence n'est perdue : _is_calendar_alert_due n'a pas de
                # fenêtre d'expiration, l'alerte reste due jusqu'à validation
                # ou esquive et repart au premier poll suivant la fin du gap.
                # Le refus 423 sur saisie 03/88 (_blocking_for_machine_impl,
                # _check_blocking_alert_due) ignore délibérément ce gap : une
                # calendaire bloquante continue d'interdire la production tant
                # qu'elle n'est pas validée, le gap n'ouvre pas de fenêtre de
                # contournement du contrôle.
                if gap_active:
                    continue
                try:
                    _created = r["created_at"] if "created_at" in r.keys() else None
                except (IndexError, KeyError):
                    _created = None
                should_show = _is_calendar_alert_due(
                    conn, int(r["id"]), params, user_machine or "", now_paris,
                    user_id=user.get("id"), created_at_iso=_created,
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
                # v2.5.32 : after_calage remonte à nouveau via le polling
                # (annule v2.2.89). Sans ça, une alerte after_calage
                # non-bloquante (block_production=False) ne s'affichait
                # JAMAIS puisque /blocking-for-machine filtre les alertes
                # bloquantes. Le comportement bloquant garde son garde-fou
                # 423 côté saisie 03/88 — ici c'est l'alerte d'écran
                # (non-bloquante) que l'opérateur peut voir et remplir.
                # Détection alignée sur _blocking_for_machine_impl (v2.3.2 :
                # match par code exact via _ALERT_CALAGE_CODES). Pas de
                # filtre opérateur : after_calage est un état machine.
                # v2.5.6 : correction du MOMENT de declenchement (le
                # comportement v2.5.32 ci-dessus est conserve pour tout le
                # reste). L'ancienne condition testait « derniere saisie de la
                # machine = code de calage » : elle devenait vraie des que
                # l'operateur pointait son calage, donc l'alerte sortait au
                # DEBUT du calage et disparaissait des la reprise. On ancre
                # desormais sur le calage lui-meme, puis on exige une reprise
                # de production (03/88) posterieure : l'alerte sort au premier
                # code de production APRES le calage -- soit a la fin du
                # calage -- et reste affichee jusqu'a validation quelles que
                # soient les saisies suivantes (le verrou reste l'ack par
                # dossier).
                if event == "after_calage" and effective_machine:
                    _calage_window = (now_paris - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%S")
                    # 1. Dernier calage de la machine dans la fenetre 4h.
                    _cal_row = conn.execute(
                        f"""SELECT no_dossier, operation_code, date_operation
                            FROM production_data
                            WHERE machine=? AND date_operation >= ?
                              AND operation_code IN {_ALERT_CALAGE_CODES_SQL_LIST}
                            ORDER BY date_operation DESC LIMIT 1""",
                        (effective_machine, _calage_window),
                    ).fetchone()
                    _dos = ""
                    if _cal_row is not None and _cal_row["no_dossier"] is not None:
                        _dos = str(_cal_row["no_dossier"]).strip()
                    if _dos:
                        _last_calage_at = _cal_row["date_operation"]
                        # 2. Reprise de production posterieure au calage :
                        #    c'est ELLE qui marque la fin du calage.
                        _prod_after = conn.execute(
                            f"""SELECT 1 FROM production_data
                                WHERE machine=? AND date_operation > ?
                                  AND operation_code IN {_ALERT_POST_CALAGE_CODES_SQL_LIST}
                                LIMIT 1""",
                            (effective_machine, _last_calage_at),
                        ).fetchone()
                        # 3. Verrou par dossier : un seul declenchement.
                        _ack_check = conn.execute(
                            """SELECT 1 FROM maintenance_alert_acks
                               WHERE alert_id=? AND no_dossier=? LIMIT 1""",
                            (int(r["id"]), _dos),
                        ).fetchone()
                        if _prod_after and not _ack_check:
                            # Contrainte v2.2.82 conservee : calage doit etre
                            # posterieur au dernier code 89 du dossier.
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
            # type manual : déclencheur obsolète (v2.5.6), jamais évalué —
            # l'alerte reste dormante jusqu'à ce que l'admin choisisse un
            # vrai déclencheur dans le formulaire.
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
    # v2.4.11 : on retire le filtre dismissed=0 pour que les esquives (bouton
    # "Pas d'Errepi" & co, v2.3.30) remontent dans l'historique. Elles sont
    # ensuite filtrées côté frontend par le toggle "Fermetures auto" — le champ
    # dismissed est renvoyé au front pour la détection (double critère avec le
    # comment "Fermée auto (esquive) : ...").
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT a.id, a.alert_id, al.nom AS alert_nom,
                       al.linked_maint_code, a.user_id, a.user_nom,
                       a.machine, a.no_dossier, a.ack_at,
                       a.responses, a.comment, a.dismissed
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
            # v2.4.11 : remonté au front pour que ctrlIsAutoClose détecte
            # aussi les anciennes esquives (dismissed=1 mais comment vide,
            # antérieures à v2.3.30 qui inscrit "Fermée auto (esquive) : …").
            "dismissed": 1 if (r["dismissed"] if "dismissed" in r.keys() else 0) else 0,
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


def _auto_ack_periodic_alerts_on_arret(conn, user, machine, no_dossier, code, code_label, operation_str, exclude_saisie_id: int = None):
    """v2.2.65 / v2.5.30 / v2.5.31 — Ferme automatiquement les alertes actives dont la
    target couvre cette machine, quand l'operateur saisit un code non-productif.
    v2.5.30 : etendu aux alertes EVENEMENTIELLES (dossier_end/dossier_start).
    v2.5.31 : etendu aux alertes CALENDAIRES (time + days).
    """
    if not machine:
        return
    from database import get_db  # noqa: F401
    now_paris = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        rows = conn.execute("SELECT id, params FROM maintenance_alerts WHERE active=1").fetchall()
    except Exception:
        return
    # v2.6.0 : accent restaure -- le reste du code (libelles UI, commentaires,
    # filtres) parle de « Fermée auto ». Les lignes deja en base sans accent
    # restent correctement filtrees : les deux orthographes sont testees cote
    # saisies.py, et ctrlIsAutoClose() cote Maintenance est deja tolerant.
    reason = (f"Fermée auto : {code} - {code_label}" if code_label else f"Fermée auto : code {code}")[:2000]
    user_id = user.get("id") if user else None
    user_nom = (user.get("nom") if user else "") or (user.get("email") if user else "") or ""
    responses_json = "{}"
    _now_dt = datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    _skip_threshold = (_now_dt - timedelta(seconds=60)).strftime("%Y-%m-%dT%H:%M:%S")
    _EVENT_TO_TRIGGER_CODE = {"dossier_end": "89", "dossier_start": "01"}
    _WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    _today_key = _WEEKDAY_KEYS[_now_dt.weekday()]
    for r in rows:
        try:
            params = _json_alerts.loads(r["params"] or "{}")
        except (ValueError, TypeError):
            continue
        trig = params.get("trigger") or {}
        ttype = trig.get("type")
        if ttype not in ("periodic", "event", "calendar"):
            continue
        if ttype == "event" and str(trig.get("event") or "").strip() == "after_calage":
            continue
        target = params.get("target") or {}
        machines_target = target.get("machines")
        if not isinstance(machines_target, list) or not machines_target:
            legacy = target.get("machine")
            machines_target = [legacy] if isinstance(legacy, str) and legacy else ["*"]
        if "*" not in machines_target and machine not in machines_target:
            continue
        try:
            recent = conn.execute(
                "SELECT 1 FROM maintenance_alert_acks WHERE alert_id=? AND machine=? AND ack_at >= ? LIMIT 1",
                (int(r["id"]), machine, _skip_threshold),
            ).fetchone()
            if recent:
                continue
        except Exception:
            pass
        was_due = False
        if ttype == "periodic":
            try:
                was_due = _is_periodic_alert_due(conn, int(r["id"]), params, machine, _now_dt, exclude_saisie_id=exclude_saisie_id)
            except Exception:
                was_due = False
        elif ttype == "event":
            event = str(trig.get("event") or "").strip()
            trigger_code = _EVENT_TO_TRIGGER_CODE.get(event)
            if not trigger_code:
                continue
            if str(code) == trigger_code:
                continue
            try:
                last_ack = conn.execute(
                    "SELECT MAX(ack_at) AS m FROM maintenance_alert_acks WHERE alert_id=? AND machine=?",
                    (int(r["id"]), machine),
                ).fetchone()
                last_ack_at_str = last_ack["m"] if last_ack else None
                _excl_sql = " AND id<>?" if exclude_saisie_id is not None else ""
                _excl_params = (int(exclude_saisie_id),) if exclude_saisie_id is not None else ()
                q = "SELECT 1 FROM production_data WHERE machine=? AND operation_code=?"
                pp = [machine, trigger_code]
                if last_ack_at_str:
                    q += " AND date_operation > ?"; pp.append(last_ack_at_str)
                else:
                    q += " AND date_operation >= ?"; pp.append(_now_dt.strftime("%Y-%m-%dT00:00:00"))
                q += _excl_sql + " LIMIT 1"
                if _excl_params:
                    pp.extend(_excl_params)
                recent_trigger = conn.execute(q, tuple(pp)).fetchone()
                was_due = recent_trigger is not None
            except Exception:
                was_due = False
        else:  # calendar
            try:
                days = trig.get("days") or []
                if not isinstance(days, list) or _today_key not in days:
                    continue
                time_str = str(trig.get("time") or "").strip()
                try:
                    hh, mm = time_str.split(":")
                    hh = int(hh); mm = int(mm)
                    if not (0 <= hh < 24 and 0 <= mm < 60):
                        raise ValueError
                except (ValueError, AttributeError):
                    continue
                fire_dt = _now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if _now_dt < fire_dt:
                    continue
                fire_iso = fire_dt.strftime("%Y-%m-%dT%H:%M:%S")
                ack_since = conn.execute(
                    "SELECT 1 FROM maintenance_alert_acks WHERE alert_id=? AND machine=? AND ack_at >= ? LIMIT 1",
                    (int(r["id"]), machine, fire_iso),
                ).fetchone()
                was_due = ack_since is None
            except Exception:
                was_due = False
        if not was_due:
            continue
        try:
            conn.execute(
                """INSERT INTO maintenance_alert_acks
                   (alert_id, user_id, user_nom, machine, no_dossier, ack_at, responses, comment)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (int(r["id"]), user_id, user_nom, machine, no_dossier or "", now_paris, responses_json, reason),
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
        # v2.4.6 : anti-doublon serveur. Defense finale contre les rafales de
        # clics. Si un ack existe deja pour (alert_id, user_id, machine) dans
        # les 5 dernieres secondes, on renvoie 200 avec le row existant SANS
        # inserer — action traitee comme idempotente, aucune erreur remontee.
        _dup_threshold = (datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
                          - timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%S")
        _dup = conn.execute(
            """SELECT id, ack_at FROM maintenance_alert_acks
               WHERE alert_id=? AND COALESCE(user_id,-1)=COALESCE(?,-1)
                 AND COALESCE(machine,'')=COALESCE(?,'')
                 AND ack_at >= ?
               ORDER BY id DESC LIMIT 1""",
            (alert_id, user.get("id"), machine or "", _dup_threshold),
        ).fetchone()
        if _dup:
            log_action(user=user, action="VALIDATE_DUP", module="maintenance_alerts",
                       objet=str(alert_id),
                       detail=f"skipped duplicate ack (existing id={_dup['id']})")
            return {"ok": True, "ack_at": _dup["ack_at"], "duplicate": True}
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
    """Fermeture explicite d'une alerte via son bouton d'esquive.

    v164 (originel) : esquive totalement silencieuse — aucun comment,
      aucun audit log.
    v2.3.30 : on garde `dismissed=1` (utile pour la logique event et pour
      exclure ces lignes des stats de conformité) mais on inscrit
      « Fermée auto (esquive) : <label du bouton> » dans le comment.
      Résultat :
        - trace visible dans l'historique /maintenance ;
        - matche le regex `^Fermée auto` donc masquée par défaut par le
          toggle « Afficher fermetures auto » ;
        - le libellé du bouton dit *pourquoi* l'op a esquivé
          (ex. « Pas d'Errepi »).

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
        # v2.3.30 : trace le libellé du bouton d'esquive dans le comment.
        _dismiss_label = str(dismiss.get("label") or "").strip() or "esquive"
        _dismiss_comment = f"Fermée auto (esquive) : {_dismiss_label}"[:2000]
        machine = _machine_name_from_user(conn, user) or ""
        conn.execute(
            """INSERT INTO maintenance_alert_acks
               (alert_id, user_id, user_nom, machine, no_dossier,
                ack_at, responses, comment, dismissed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (alert_id, user.get("id"), user.get("nom") or user.get("email") or "",
             machine, "", now_paris, "{}", _dismiss_comment),
        )
        conn.execute(
            "UPDATE maintenance_alerts SET last_ack_at=?, updated_at=? WHERE id=?",
            (now_paris, now_paris, alert_id),
        )
        conn.commit()
    return {"ok": True, "dismissed": True}


# ─── Pièces d'usure — CRUD du référentiel (v229) ─────────────────────────────
# Remplace les 4 pièces qui vivaient en dur dans WEARPART_PIECES (front) et le
# matching par libellé qui les reliait aux codes. L'ancien endpoint
# /api/maintenance/wearparts/last vivait ici : il scannait production_data avec
# des LIKE '%contre%couteaux%bande%' et n'était plus appelé par personne depuis
# le passage à /wearparts/info — supprimé avec le reste du matching textuel.


def _usure_slugify(label: str, taken: set) -> str:
    """Clé stable dérivée du libellé, unique dans la table.

    La clé ne change JAMAIS ensuite : c'est elle qui indexe le cache et le
    localStorage du front (mysifa_maint_wearparts_v1). Renommer une pièce doit
    rester sans conséquence sur l'onglet mémorisé par chaque utilisateur.
    """
    import re as _re
    import unicodedata
    s = unicodedata.normalize("NFD", str(label or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    s = _re.sub(r"[^a-z0-9]+", "_", s).strip("_")[:40] or "piece"
    base, i = s, 2
    while s in taken:
        s = f"{base}_{i}"[:40]
        i += 1
    return s


@router.get("/api/maintenance/usure-pieces")
def usure_pieces_list(request: Request, include_inactifs: bool = False):
    """Référentiel des pièces d'usure. Lecture ouverte à tout utilisateur
    connecté : l'accueil Maintenance en a besoin pour rendre ses cartes."""
    get_current_user(request)
    from database import get_db
    with get_db() as conn:
        if not _ensure_usure_table(conn):
            return {"items": [], "migrated": False}
        where = "" if include_inactifs else "WHERE actif = 1"
        rows = conn.execute(
            f"""SELECT id, cle, label, ordre, actif
                FROM maintenance_usure_pieces
                {where}
                ORDER BY ordre ASC, label ASC"""
        ).fetchall()
        counts = {}
        try:
            for cr in conn.execute(
                """SELECT usure_piece_id AS pid, COUNT(*) AS n
                   FROM maintenance_codes WHERE usure_piece_id IS NOT NULL
                   GROUP BY usure_piece_id"""
            ).fetchall():
                counts[int(cr["pid"])] = int(cr["n"])
        except Exception:
            counts = {}
        # v230 : positions déduites des codes rattachés, pièce par pièce.
        positions_by_piece = {
            int(r["id"]): _usure_positions_from_codes(conn, int(r["id"])) for r in rows
        }
    items = [
        _usure_piece_row_to_dict(
            r, counts.get(int(r["id"]), 0), positions_by_piece.get(int(r["id"]), [])
        )
        for r in rows
    ]
    return {"items": items, "migrated": True}


@router.post("/api/maintenance/usure-pieces")
async def usure_pieces_create(request: Request):
    user = _require_maint_writer(request)
    body = await request.json()
    label = (body.get("label") or "").strip()[:80]
    if not label:
        raise HTTPException(422, "Libellé obligatoire.")
    try:
        ordre = int(body.get("ordre") or 0)
    except (TypeError, ValueError):
        ordre = 0
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        if not _ensure_usure_table(conn):
            raise HTTPException(500, "Migration DB manquante (maintenance_usure_pieces absente).")
        taken = {r["cle"] for r in conn.execute(
            "SELECT cle FROM maintenance_usure_pieces").fetchall()}
        cle = _usure_slugify(label, taken)
        if ordre <= 0:
            row = conn.execute(
                "SELECT COALESCE(MAX(ordre),0) AS m FROM maintenance_usure_pieces").fetchone()
            ordre = int(row["m"] or 0) + 1
        cur = conn.execute(
            """INSERT INTO maintenance_usure_pieces
               (cle,label,positions,ordre,actif,created_at,updated_at)
               VALUES (?,?,'[]',?,1,?,?)""",
            (cle, label, ordre, now, now),
        )
        conn.commit()
        new_id = cur.lastrowid
    log_action(user=user, action="CREATE", module="maintenance_usure_pieces",
               objet=cle, detail=label)
    return {"ok": True, "id": new_id, "cle": cle}


@router.put("/api/maintenance/usure-pieces/{piece_id}")
async def usure_pieces_update(piece_id: int, request: Request):
    """Renommer, réordonner, activer/désactiver, changer les positions.

    La `cle` n'est jamais modifiée : c'est le point qui rend le renommage
    inoffensif côté front (cache + localStorage indexés dessus).
    """
    user = _require_maint_writer(request)
    body = await request.json()
    from database import get_db
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        if not _ensure_usure_table(conn):
            raise HTTPException(500, "Migration DB manquante (maintenance_usure_pieces absente).")
        row = conn.execute(
            "SELECT id, cle, label, ordre, actif FROM maintenance_usure_pieces WHERE id=?",
            (piece_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Pièce introuvable.")
        label = (body.get("label") or row["label"]).strip()[:80]
        if not label:
            raise HTTPException(422, "Libellé obligatoire.")
        # v230 : `positions` n'est plus modifiable ici — elle se déduit des
        # codes. Un client qui l'enverrait encore est ignoré silencieusement
        # plutôt que refusé : le champ n'existe plus dans le formulaire.
        try:
            ordre = int(body["ordre"]) if "ordre" in body else int(row["ordre"] or 0)
        except (TypeError, ValueError):
            ordre = int(row["ordre"] or 0)
        actif = int(bool(body["actif"])) if "actif" in body else int(bool(row["actif"]))
        if not actif:
            n_used = conn.execute(
                "SELECT COUNT(*) AS n FROM maintenance_codes WHERE usure_piece_id=?",
                (piece_id,),
            ).fetchone()["n"]
            if n_used:
                raise HTTPException(
                    409,
                    f"{n_used} code(s) sont encore rattachés à « {row['label']} ». "
                    "Détachez-les avant de désactiver la pièce.",
                )
        conn.execute(
            """UPDATE maintenance_usure_pieces
               SET label=?, ordre=?, actif=?, updated_at=?
               WHERE id=?""",
            (label, ordre, actif, now, piece_id),
        )
        conn.commit()
        cle = row["cle"]
    log_action(user=user, action="UPDATE", module="maintenance_usure_pieces",
               objet=cle, detail=label)
    return {"ok": True}


@router.delete("/api/maintenance/usure-pieces/{piece_id}")
def usure_pieces_delete(piece_id: int, request: Request):
    user = _require_maint_writer(request)
    from database import get_db
    with get_db() as conn:
        if not _ensure_usure_table(conn):
            raise HTTPException(500, "Migration DB manquante (maintenance_usure_pieces absente).")
        row = conn.execute(
            "SELECT cle, label FROM maintenance_usure_pieces WHERE id=?", (piece_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Pièce introuvable.")
        n_used = conn.execute(
            "SELECT COUNT(*) AS n FROM maintenance_codes WHERE usure_piece_id=?",
            (piece_id,),
        ).fetchone()["n"]
        if n_used:
            raise HTTPException(
                409,
                f"{n_used} code(s) sont rattachés à « {row['label']} ». "
                "Détachez-les avant de supprimer la pièce.",
            )
        conn.execute("DELETE FROM maintenance_usure_pieces WHERE id=?", (piece_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="maintenance_usure_pieces",
               objet=row["cle"], detail=row["label"])
    return {"ok": True}


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
