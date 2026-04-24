from fastapi import APIRouter, Request
from database import get_db
from services.auth_service import get_current_user, is_admin, is_fabrication

router = APIRouter()

@router.get("/api/filters")
def get_filters(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        if is_admin(user):
            # Admin: voir tous les opérateurs qui ont saisi
            ops = conn.execute("""
                SELECT DISTINCT operateur FROM production_data
                WHERE operateur IS NOT NULL AND operateur!=''
                ORDER BY operateur
            """).fetchall()
        elif is_fabrication(user):
            # Fabrication: uniquement son propre nom (operateur_lie ou nom utilisateur)
            user_operateur = user.get("operateur_lie") or user.get("nom") or ""
            ops = conn.execute("""
                SELECT DISTINCT operateur FROM production_data
                WHERE operateur=? ORDER BY operateur
            """, (user_operateur,)).fetchall()
        else:
            # Autres rôles: voir les utilisateurs qui ont saisi (basé sur modifie_par email -> nom)
            # On retourne les noms d'utilisateurs qui ont fait des saisies manuelles
            rows = conn.execute("""
                SELECT DISTINCT modifie_par FROM production_data
                WHERE modifie_par IS NOT NULL AND est_manuel=1
                ORDER BY modifie_par
            """).fetchall()
            # Convertir emails en noms (en utilisant la table users)
            emails = [r["modifie_par"] for r in rows if r["modifie_par"]]
            if emails:
                placeholders = ','.join('?' * len(emails))
                user_rows = conn.execute(f"""
                    SELECT DISTINCT nom FROM users
                    WHERE email IN ({placeholders}) AND actif=1
                    ORDER BY nom
                """, emails).fetchall()
                ops = [{"operateur": r["nom"]} for r in user_rows]
            else:
                ops = []

        dos = conn.execute("""
            SELECT DISTINCT no_dossier FROM production_data
            WHERE no_dossier IS NOT NULL AND no_dossier!='' AND no_dossier!='0'
            ORDER BY no_dossier
        """).fetchall()
        machines = conn.execute("""
            SELECT DISTINCT machine FROM production_data
            WHERE machine IS NOT NULL AND machine!=''
            ORDER BY machine
        """).fetchall()

    return {
        "operators": [r["operateur"] for r in ops],
        "dossiers":  [r["no_dossier"] for r in dos],
        "machines":  [r["machine"]    for r in machines],
    }
