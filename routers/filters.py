from fastapi import APIRouter, Request
from database import get_db
from services.auth_service import get_current_user, is_admin

router = APIRouter()

@router.get("/api/filters")
def get_filters(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        if is_admin(user):
            ops = conn.execute("SELECT DISTINCT operateur FROM production_data WHERE operateur IS NOT NULL AND operateur!='' ORDER BY operateur").fetchall()
        else:
            # Fabrication : uniquement son propre opérateur
            ops = conn.execute("SELECT DISTINCT operateur FROM production_data WHERE operateur=? ORDER BY operateur",
                               (user.get("operateur_lie",""),)).fetchall()
        dos      = conn.execute("SELECT DISTINCT no_dossier FROM production_data WHERE no_dossier IS NOT NULL AND no_dossier!='' AND no_dossier!='0' ORDER BY no_dossier").fetchall()
        machines = conn.execute("SELECT DISTINCT machine FROM production_data WHERE machine IS NOT NULL AND machine!='' ORDER BY machine").fetchall()
    return {
        "operators": [r["operateur"] for r in ops],
        "dossiers":  [r["no_dossier"] for r in dos],
        "machines":  [r["machine"]    for r in machines],
    }
