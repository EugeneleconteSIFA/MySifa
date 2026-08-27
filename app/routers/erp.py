"""API ERP — lecture seule du miroir RVGI.

Ouvert à la direction et aux services administration, en plus du super
administrateur — c'est `ROLES_ADMIN`, le même périmètre que les autres
fonctions d'administration de MySifa. La page `/erp` en est le seul
consommateur.

Endpoints
---------
  GET /api/erp/meta                    → fraîcheur du miroir, écrans disponibles
  GET /api/erp/tdb/{cle}               → un tableau de bord (adv | direction)
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
from app.services import erp_tdb
from app.services.auth_service import get_current_user
from config import ROLES_ADMIN

router = APIRouter(prefix="/api/erp", tags=["erp"])


def _exiger_acces(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in ROLES_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé à la direction, aux services administration et au super administrateur.",
        )
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
    user = _exiger_acces(request)
    infos = miroir.meta()
    if not infos["present"]:
        return {
            "present": False,
            "menu": catalogue.menu_du_role(user.get("role"), set()),
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
            "rattachable": bool(adapte.get("rattachable")),
        })

    # Les écrans sortent dans l'ordre d'affichage, pas dans celui du catalogue.
    ecrans.sort(key=lambda e: catalogue.rang(e["cle"]))

    return {
        "present": True,
        "menu": catalogue.menu_du_role(user.get("role"), {e["cle"] for e in ecrans}),
        "importe_le": infos["importe_le"],
        "releve_le": infos["releve_le"],
        "lignes": infos["lignes"],
        "tables": len(infos["tables"]),
        "domaines": catalogue.DOMAINES,
        "ecrans": ecrans,
        "enums": catalogue.ENUMS,
    }


@router.get("/recherche")
def erp_recherche(
    request: Request,
    q: str = Query("", max_length=120),
    par_ecran: int = Query(miroir.RESULTATS_PAR_ECRAN, ge=1, le=20),
):
    """Cherche la même chaîne dans les vingt-sept écrans à la fois.

    Déclarée AVANT `/{cle}/...` : sinon FastAPI lirait « recherche » comme une
    clé d'écran et rendrait un 404.
    """
    _exiger_acces(request)
    cols = _colonnes_par_table()
    ecrans = []
    for ec in catalogue.ECRANS:
        adapte = catalogue.adapter_ecran(ec, cols)
        if adapte:
            ecrans.append(adapte)
    ecrans.sort(key=lambda e: catalogue.rang(e["cle"]))
    try:
        return miroir.recherche_globale(ecrans, q, par_ecran=par_ecran)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/tdb/{cle}")
def erp_tableau_de_bord(cle: str, request: Request):
    """Un tableau de bord monté sur le miroir.

    Déclarée AVANT `/{cle}/...`, comme `/recherche` : sinon FastAPI lirait
    « tdb » comme une clé d'écran.

    Les compteurs qui vivent dans MySifa — OF, fiches techniques, mappings,
    scans — ne passent PAS par ici. Le navigateur va les chercher à leur
    propre route, celle-là même que le lien de la tuile ouvre : un compteur
    et l'écran qu'il ouvre ne peuvent alors jamais diverger.
    """
    _exiger_acces(request)
    if cle not in ("adv", "direction"):
        raise HTTPException(status_code=404, detail="Tableau de bord inconnu.")
    try:
        return erp_tdb.adv() if cle == "adv" else erp_tdb.direction()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/{cle}/lignes")
def erp_lignes(
    cle: str,
    request: Request,
    q: str = Query("", max_length=120),
    tri: str = Query("", max_length=60),
    sens: str = Query("asc", max_length=4),
    page: int = Query(1, ge=1, le=100000),
    taille: int = Query(miroir.TAILLE_PAGE_DEFAUT, ge=1, le=miroir.TAILLE_PAGE_MAX),
    depuis: str = Query("", max_length=40),
    depuis_id: str = Query("", max_length=40),
    lien: int = Query(-1, ge=-1, le=99),
    ratt: str = Query("", max_length=10),
):
    _exiger_acces(request)
    ec = _ecran(cle)
    if ratt and ratt not in ("oui", "non", "partiel", "douteux"):
        raise HTTPException(status_code=400, detail="Filtre de rattachement inconnu.")

    # Ouverture depuis une pièce liée : le client donne l'écran d'origine, la
    # ligne et le rang du lien — jamais un nom de colonne. La condition est
    # reconstruite ici, à partir du catalogue.
    extra = None
    contexte = None
    if depuis and depuis_id and lien >= 0:
        extra, contexte = _condition_de_lien(depuis, depuis_id, lien, cle)

    # Les filtres arrivent en `f_<nom>` : seuls ceux que l'écran déclare sont
    # retenus, les autres sont ignorés sans bruit.
    filtres = {}
    for nom_param, valeur in request.query_params.items():
        if nom_param.startswith("f_"):
            filtres[nom_param[2:]] = valeur

    try:
        res = miroir.lister(
            ec, q=q, filtres=filtres, tri=tri or None, sens=sens,
            page=page, taille=taille, extra=extra,
            rattachement=bool(ec.get("rattachable")), filtre_ratt=ratt,
        )
        if contexte:
            res["contexte"] = contexte
        return res
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _condition_de_lien(cle_source, ident, rang, cle_cible):
    """Reconstruit la condition d'un lien déclaré au catalogue."""
    ec_source = catalogue.ecran(cle_source)
    if not ec_source:
        raise HTTPException(status_code=400, detail="Écran d'origine inconnu.")
    liens = catalogue.LIENS.get(cle_source, [])
    if rang >= len(liens):
        raise HTTPException(status_code=400, detail="Lien inconnu.")
    lien = liens[rang]
    if lien["ecran"] != cle_cible:
        raise HTTPException(status_code=400, detail="Ce lien ne mène pas à cet écran.")

    adapte = catalogue.adapter_ecran(ec_source, _colonnes_par_table())
    if not adapte:
        raise HTTPException(status_code=404, detail="Écran d'origine indisponible.")

    source = miroir.ligne_brute(adapte, ident)
    if source is None:
        raise HTTPException(status_code=404, detail="Ligne d'origine introuvable.")

    extra = []
    valeurs = {}
    for ref, champ in lien["sur"].items():
        v = source.get(champ)
        if v is None or str(v).strip() == "":
            raise HTTPException(status_code=400, detail="La ligne d'origine ne porte pas cette clé.")
        extra.append(("CAST(%s AS TEXT) = ?" % miroir.valider_ref(ref), str(v).strip()))
        valeurs[ref.split(".")[-1]] = v

    return extra, {
        "depuis": cle_source,
        "depuis_label": ec_source["label"],
        "lien": lien["label"],
        "valeurs": valeurs,
    }


@router.get("/{cle}/liens/{ident}")
def erp_liens(cle: str, ident: str, request: Request):
    """Les pièces rattachées à une ligne : BL d'une commande, facture d'un BL…"""
    _exiger_acces(request)
    ec = _ecran(cle)
    cols = _colonnes_par_table()

    def resoudre(cle_cible):
        cible = catalogue.ecran(cle_cible)
        if not cible:
            return None
        return catalogue.adapter_ecran(cible, cols)

    try:
        return {"liens": miroir.liens(ec, ident, resoudre)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/{cle}/detail/{ident}")
def erp_detail(cle: str, ident: str, request: Request):
    """La ligne ouverte, et la pièce qui la porte.

    Sur un écran de lignes de document — commande, marché, BL, facture — on
    renvoie d'un seul coup l'entête de la pièce et TOUTES ses lignes. Ouvrir la
    ligne 2 d'un marché sans montrer qu'il en compte quatre oblige à retourner
    à la grille : c'est justement le geste que cet écran doit supprimer.
    """
    _exiger_acces(request)
    ec = _ecran(cle)
    try:
        piece = miroir.piece(ec, ident)
        # Ce que l'entête porte déjà n'est pas répété dans le détail de la
        # ligne. Uniquement ce qui lui est PROPRE : `amje` existe des deux
        # côtés — date d'échéance de la pièce et de la ligne — et l'écarter du
        # détail ferait disparaître une information qui n'est pas la même.
        exclure = set()
        entete = None
        if piece:
            cols_ligne = _colonnes_par_table().get(ec["table"], set())
            exclure = set(piece["colonnes_entete"]) - set(cols_ligne) - {"numero"}
            entete = piece.get("brut_entete")
        res = miroir.detail(ec, ident, exclure=exclure, entete=entete)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if res is None:
        raise HTTPException(status_code=404, detail="Ligne introuvable dans le miroir.")
    if piece:
        piece.pop("colonnes_entete", None)
        piece.pop("brut_entete", None)
        res["piece"] = piece
    return res
