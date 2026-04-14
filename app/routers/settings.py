"""Paramètres & matrice d'accès — super administrateur uniquement."""

from fastapi import APIRouter, Request

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
            "label": "Planning",
            "hint": "Planning atelier (même périmètre que MyProd pour les rôles)",
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
