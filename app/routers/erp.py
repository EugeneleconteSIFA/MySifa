"""API ERP — lecture seule du miroir RVGI.

Réservé au super administrateur. La page `/erp` en est le seul consommateur.

Endpoints
---------
  GET /api/erp/meta                    → fraîcheur du miroir, écrans disponibles
  GET /api/erp/{ecran}/lignes          → liste paginée, filtrée, triée
  GET /api/erp/{ecran}/detail/{id}     → toutes les colonnes d'une ligne

Aucun POST, aucun PUT, aucun DELETE — et ce n'est pas une omission : le miroir
est ouvert en `mode=ro` par `app/services/erp_mirror.py`. RVGI est la source,
MySifa lit. Le jour où l'on voudra écrire, ce sera un autre chantier, avec
l'accord de l'éditeur de l'ERP.
"""

from fastapi import APIRouter, HTTPException, Query, Request

from app.services import erp_catalogue as catalogue
from app.services import erp_mirror as miroir
from app.services.auth_service import get_current_user
from config import ROLE_SUPERADMIN

router = APIRouter(prefix="/api/erp", tags=["erp"])


def _exiger_acces(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") != ROLE_SUPERADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé au super administrateur.")
    return user


def _colonnes_par_table():
    """Ce que le miroir contient réellement, table par table.

    Miroir absent = 503 (« le service n'est pas disponible »), pas 500 : ce
    n'est pas un bug de MySifa, c'est un import qui n'a pas encore eu lieu, et
    le message le dit.
    """
    try:
        with miroir.get_erp_db() as conn:
            tables = miroir.tables_presentes(conn)
            return {
                t: {r[1] for r in conn.execute("SELECT * FROM pragma_table_info(?)", (t,))}
                for t in tables
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


def _ecran(cle):
    ec = catalogue.ecran(cle)
    if not ec:
        raise HTTPException(status_code=404, detail="Écran inconnu.")
    adapte = catalogue.adapter_ecran(ec, _colonnes_par_table())
    if not adapte:
        raise HTTPException(
            status_code=404,
            detail="Écran indisponible : la table « %s » n'est pas dans le miroir." % ec["table"],
        )
    return adapte


@router.get("/meta")
def erp_meta(request: Request):
    _exiger_acces(request)
    infos = miroir.meta()
    if not infos["present"]:
        return {
            "present": False,
            "domaines": catalogue.DOMAINES,
            "ecrans": [],
            "enums": catalogue.ENUMS,
            "message": (
                "Le miroir de l'ERP n'a pas encore été construit. "
                "Lancer l'export depuis un poste du réseau SIFA, puis l'import."
            ),
        }

    cols = _colonnes_par_table()
    lignes_par_table = {t["nom"]: t["lignes"] for t in infos["tables"]}
    ecrans = []
    for ec in catalogue.ECRANS:
        adapte = catalogue.adapter_ecran(ec, cols)
        if not adapte:
            continue
        ecrans.append({
            "cle": ec["cle"],
            "label": ec["label"],
            "domaine": ec["domaine"],
            "resume": ec.get("resume", ""),
            "table": ec["table"],
            "lignes": lignes_par_table.get(ec["table"]),
            "colonnes": len(adapte["colonnes"]),
            "filtres": [
                {k: v for k, v in f.items() if k != "col"} for f in adapte["filtres"]
            ],
        })

    return {
        "present": True,
        "importe_le": infos["importe_le"],
        "releve_le": infos["releve_le"],
        "lignes": infos["lignes"],
        "tables": len(infos["tables"]),
        "domaines": catalogue.DOMAINES,
        "ecrans": ecrans,
        "enums": catalogue.ENUMS,
    }


@router.get("/{cle}/lignes")
def erp_lignes(
    cle: str,
    request: Request,
    q: str = Query("", max_length=120),
    tri: str = Query("", max_length=60),
    sens: str = Query("asc", max_length=4),
    page: int = Query(1, ge=1, le=100000),
    taille: int = Query(miroir.TAILLE_PAGE_DEFAUT, ge=1, le=miroir.TAILLE_PAGE_MAX),
):
    _exiger_acces(request)
    ec = _ecran(cle)

    # Les filtres arrivent en `f_<nom>` : seuls ceux que l'écran déclare sont
    # retenus, les autres sont ignorés sans bruit.
    filtres = {}
    for nom_param, valeur in request.query_params.items():
        if nom_param.startswith("f_"):
            filtres[nom_param[2:]] = valeur

    try:
        return miroir.lister(
            ec, q=q, filtres=filtres, tri=tri or None, sens=sens,
            page=page, taille=taille,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{cle}/detail/{ident}")
def erp_detail(cle: str, ident: str, request: Request):
    _exiger_acces(request)
    ec = _ecran(cle)
    try:
        res = miroir.detail(ec, ident)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if res is None:
        raise HTTPException(status_code=404, detail="Ligne introuvable dans le miroir.")
    return res
