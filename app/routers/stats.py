"""SIFA — Stats v0.6"""
from fastapi import APIRouter, Request
from database import get_db
from services.auth_service import require_admin
from config import APP_VERSION, OPERATION_SEVERITY

router = APIRouter()

@router.get("/api/dashboard/stats")
def dashboard_stats(request: Request):
    require_admin(request)
    with get_db() as conn:
        ti = conn.execute("SELECT COUNT(*) as c FROM imports").fetchone()["c"]
        tr = conn.execute("SELECT COALESCE(SUM(row_count),0) as c FROM imports").fetchone()["c"]
        li = conn.execute("SELECT * FROM imports ORDER BY imported_at DESC LIMIT 1").fetchone()
        td = conn.execute("SELECT COUNT(*) as c FROM dossiers").fetchone()["c"]
        cr = conn.execute("SELECT COUNT(*) as c FROM production_data WHERE operation_severity='critique'").fetchone()["c"]
        at = conn.execute("SELECT COUNT(*) as c FROM production_data WHERE operation_severity='attention'").fetchone()["c"]
    return {"total_imports":ti,"total_rows":tr,"total_dossiers":td,
            "last_import":dict(li) if li else None,"critiques":cr,"attentions":at}

@router.get("/api/config/operations")
def get_ops_config():
    """Même source que le moteur d’import (config.OPERATION_SEVERITY — operations.json validé au démarrage)."""
    return OPERATION_SEVERITY

@router.get("/api/health")
def health():
    return {"status":"ok","version":APP_VERSION}
