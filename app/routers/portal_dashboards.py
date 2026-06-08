"""API — tableaux de bord personnalisés sur le portail."""
from fastapi import APIRouter, Request

from database import get_db
from services.auth_service import get_current_user
from app.services.portal_dashboard_service import (
    catalog_for_user,
    portal_dashboards_list_from_db,
    widgets_payload,
)

router = APIRouter()


@router.get("/api/portal/dashboards/catalog")
def portal_dashboards_catalog(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT portal_dashboards FROM users WHERE id = ? LIMIT 1",
            (user["id"],),
        ).fetchone()
    enabled = portal_dashboards_list_from_db(row["portal_dashboards"] if row else None)
    catalog = catalog_for_user(user)
    return {"catalog": catalog, "enabled": enabled}


@router.get("/api/portal/dashboards/data")
def portal_dashboards_data(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT portal_dashboards FROM users WHERE id = ? LIMIT 1",
            (user["id"],),
        ).fetchone()
        enabled = portal_dashboards_list_from_db(row["portal_dashboards"] if row else None)
        widgets = widgets_payload(conn, user, enabled)
    return {"widgets": widgets}
